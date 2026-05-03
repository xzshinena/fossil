package fossil

import akka.actor.ActorSystem
import akka.stream.scaladsl.{Flow, Sink, Source}
import com.google.cloud.pubsub.v1.Publisher
import com.google.protobuf.ByteString
import com.google.pubsub.v1.PubsubMessage
import io.circe.parser.decode
import io.circe.syntax._
import org.slf4j.LoggerFactory
import zio._
import zio.interop.reactivestreams._

import java.time.Instant

object StreamingPipeline {
  private val log = LoggerFactory.getLogger(getClass)

  def run(config: Config): Task[Unit] = {
    implicit val system: ActorSystem = ActorSystem("fossil-streaming")

    for {
      stateRef   <- Ref.make(Map.empty[String, List[WindowEntry]])
      stub        = PubSubSource.makeSubscriberStub(config)
      publisher   = PubSubSource.makePublisher(config, config.scoreUpdatesTopic)
      _          <- ZIO.attempt(PubSubSource.ensureSubscription(stub, config))
      subPath     = com.google.pubsub.v1.ProjectSubscriptionName.format(
                      config.projectId, config.rawEventsSubscription)
      source      = new PubSubSource(stub, subPath)
      akkaSource  = Source.fromPublisher(source)
      // Parse JSON bytes → RawEvent via Akka flow (CPU-bound, stays on Akka dispatcher)
      parsedSrc   = akkaSource.via(parseFlow)
      reactPub    = parsedSrc.runWith(Sink.asPublisher(fanout = false))
      zioStream   = reactPub.toZIOStream(bufferSize = 32)
      _          <- zioStream
                      .mapZIO { event =>
                        RollingWindow
                          .addEvent(stateRef, event.language, event.rawValue)
                          .map(total => (event, total))
                      }
                      .map { case (event, total) => buildScoreUpdate(event, total) }
                      .collectSome
                      .mapZIO(update => publishUpdate(publisher, update))
                      .runDrain
    } yield ()
  }

  private val parseFlow: akka.stream.scaladsl.Flow[Array[Byte], RawEvent, _] =
    Flow[Array[Byte]].mapConcat { bytes =>
      decode[RawEvent](new String(bytes, "UTF-8")) match {
        case Right(event) => List(event)
        case Left(err) =>
          log.warn("Failed to parse RawEvent: {}", err.getMessage)
          Nil
      }
    }

  private def buildScoreUpdate(event: RawEvent, windowTotal: Double): Option[ScoreUpdate] =
    event.languageId.map { langId =>
      ScoreUpdate(
        languageId   = langId,
        language     = event.language,
        subScoreType = event.source,
        delta        = event.rawValue,
        newScore     = windowTotal,
        timestamp    = Instant.now().toString,
      )
    }

  private def publishUpdate(publisher: Publisher, update: ScoreUpdate): Task[Unit] =
    ZIO.attempt {
      val json    = update.asJson.noSpaces
      val message = PubsubMessage.newBuilder()
        .setData(ByteString.copyFromUtf8(json))
        .build()
      publisher.publish(message)
      log.debug("Published score update for language={} score={}", update.language, update.newScore)
    }
}
