package fossil

import zio._

object RollingWindow {
  private val WindowMs = 30L * 24 * 60 * 60 * 1000 // 30 days in ms

  /** Add a new event value for a language and return the updated 30-day window total. */
  def addEvent(
    ref:      Ref[Map[String, List[WindowEntry]]],
    language: String,
    value:    Double,
  ): UIO[Double] = {
    val now    = java.time.Instant.now().toEpochMilli
    val cutoff = now - WindowMs
    ref.modify { state =>
      val existing = state.getOrElse(language, Nil).filter(_.timestampMs > cutoff)
      val updated  = WindowEntry(now, value) :: existing
      val total    = updated.map(_.value).sum
      (total, state.updated(language, updated))
    }
  }
}
