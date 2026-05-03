package fossil

import com.google.api.gax.core.NoCredentialsProvider
import com.google.api.gax.grpc.GrpcTransportChannel
import com.google.api.gax.rpc.FixedTransportChannelProvider
import com.google.cloud.pubsub.v1.stub.{GrpcSubscriberStub, SubscriberStubSettings}
import com.google.cloud.pubsub.v1.{Publisher, TopicAdminClient, TopicAdminSettings}
import com.google.protobuf.ByteString
import com.google.pubsub.v1._
import io.grpc.ManagedChannelBuilder
import org.reactivestreams.{Publisher => ReactivePublisher, Subscriber, Subscription}
import org.slf4j.LoggerFactory

import scala.jdk.CollectionConverters._

object PubSubSource {
  private val log = LoggerFactory.getLogger(getClass)

  private def channelProvider(host: String): FixedTransportChannelProvider = {
    val channel = ManagedChannelBuilder.forTarget(host).usePlaintext().build()
    FixedTransportChannelProvider.create(GrpcTransportChannel.create(channel))
  }

  def makeSubscriberStub(config: Config): GrpcSubscriberStub = {
    val settings = config.emulatorHost match {
      case Some(host) =>
        SubscriberStubSettings.newBuilder()
          .setTransportChannelProvider(channelProvider(host))
          .setCredentialsProvider(NoCredentialsProvider.create())
          .build()
      case None =>
        SubscriberStubSettings.newBuilder().build()
    }
    GrpcSubscriberStub.create(settings)
  }

  def makePublisher(config: Config, topic: String): Publisher = {
    val topicName = TopicName.of(config.projectId, topic)
    ensureTopic(config, topic)
    config.emulatorHost match {
      case Some(host) =>
        Publisher.newBuilder(topicName)
          .setChannelProvider(channelProvider(host))
          .setCredentialsProvider(NoCredentialsProvider.create())
          .build()
      case None =>
        Publisher.newBuilder(topicName).build()
    }
  }

  private def ensureTopic(config: Config, topic: String): Unit = {
    val topicName = TopicName.of(config.projectId, topic)
    val settings = config.emulatorHost match {
      case Some(host) =>
        TopicAdminSettings.newBuilder()
          .setTransportChannelProvider(channelProvider(host))
          .setCredentialsProvider(NoCredentialsProvider.create())
          .build()
      case None =>
        TopicAdminSettings.newBuilder().build()
    }
    val admin = TopicAdminClient.create(settings)
    try { admin.createTopic(topicName) }
    catch { case _: com.google.api.gax.rpc.AlreadyExistsException => }
    finally { admin.close() }
  }

  def ensureSubscription(stub: GrpcSubscriberStub, config: Config): Unit = {
    val subPath = ProjectSubscriptionName.format(config.projectId, config.rawEventsSubscription)
    val topicPath = ProjectTopicName.format(config.projectId, config.rawEventsTopic)
    val req = Subscription.newBuilder()
      .setName(subPath)
      .setTopic(topicPath)
      .setAckDeadlineSeconds(20)
      .build()
    try {
      stub.createSubscriptionCallable().call(req)
      log.info("Created subscription {}", subPath)
    } catch {
      case _: com.google.api.gax.rpc.AlreadyExistsException =>
        log.debug("Subscription {} already exists", subPath)
    }
  }
}

/**
 * A reactive streams Publisher[Array[Byte]] that wraps the synchronous
 * Pub/Sub pull API. Each call to Subscription.request(n) pulls up to n
 * messages, delivers them to the Subscriber, then acknowledges them.
 *
 * This is the source side of the ZIO ↔ Akka Streams interop bridge:
 *   val zioStream = pubSubSource.toZIOStream(bufferSize = 32)
 */
class PubSubSource(stub: GrpcSubscriberStub, subscriptionPath: String)
    extends ReactivePublisher[Array[Byte]] {

  private val log = LoggerFactory.getLogger(getClass)

  override def subscribe(subscriber: Subscriber[_ >: Array[Byte]]): Unit =
    subscriber.onSubscribe(new Subscription {
      @volatile private var cancelled = false

      override def request(n: Long): Unit = {
        if (cancelled) return
        try {
          val maxMessages = math.min(n, 10L).toInt
          val pullReq = PullRequest.newBuilder()
            .setSubscription(subscriptionPath)
            .setMaxMessages(maxMessages)
            .build()
          val response = stub.pullCallable().call(pullReq)
          val messages = response.getReceivedMessagesList.asScala.toList

          if (messages.isEmpty) {
            Thread.sleep(200) // backpressure: no messages available
          } else {
            val ackIds = messages.map(_.getAckId)
            messages.foreach(m => subscriber.onNext(m.getMessage.getData.toByteArray))
            val ackReq = AcknowledgeRequest.newBuilder()
              .setSubscription(subscriptionPath)
              .addAllAckIds(ackIds.asJava)
              .build()
            stub.acknowledgeCallable().call(ackReq)
          }
        } catch {
          case e: InterruptedException =>
            Thread.currentThread().interrupt()
            subscriber.onError(e)
          case e: Throwable =>
            log.error("PubSubSource pull error", e)
            subscriber.onError(e)
        }
      }

      override def cancel(): Unit = { cancelled = true }
    })
}
