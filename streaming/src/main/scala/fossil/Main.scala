package fossil

import zio._

object Main extends ZIOAppDefault {
  override def run: ZIO[ZIOAppArgs & Scope, Any, Any] = {
    val config = Config.load()
    StreamingPipeline
      .run(config)
      .tapError(e => ZIO.logError(s"Streaming pipeline failed: ${e.getMessage}"))
      .retry(Schedule.exponential(2.seconds) && Schedule.recurs(5))
  }
}
