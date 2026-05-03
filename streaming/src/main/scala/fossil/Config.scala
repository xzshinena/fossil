package fossil

/** Runtime configuration read from environment variables. */
case class Config(
  projectId:           String,
  rawEventsTopic:      String,
  rawEventsSubscription: String,
  scoreUpdatesTopic:   String,
  emulatorHost:        Option[String],
)

object Config {
  def load(): Config = Config(
    projectId             = sys.env.getOrElse("PUBSUB_PROJECT_ID", "fossil-dev"),
    rawEventsTopic        = "raw-events",
    rawEventsSubscription = "scala-streaming",
    scoreUpdatesTopic     = "score-updates",
    emulatorHost          = sys.env.get("PUBSUB_EMULATOR_HOST").filter(_.nonEmpty),
  )
}
