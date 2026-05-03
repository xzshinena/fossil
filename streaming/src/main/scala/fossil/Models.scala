package fossil

import io.circe.{Decoder, Encoder}
import io.circe.generic.semiauto._

/** Raw event published by the Python ingest scripts to the raw-events topic. */
case class RawEvent(
  source:     String,
  language:   String,
  languageId: Option[Int],
  year:       Int,
  month:      Int,
  rawValue:   Double,
)

object RawEvent {
  implicit val decoder: Decoder[RawEvent] = Decoder.instance { c =>
    for {
      source     <- c.downField("source").as[String]
      language   <- c.downField("language").as[String]
      langId     <- c.downField("language_id").as[Option[Int]]
      year       <- c.downField("year").as[Int]
      month      <- c.downField("month").as[Int]
      rawValue   <- c.downField("raw_value").as[Double]
    } yield RawEvent(source, language, langId, year, month, rawValue)
  }
}

/** Delta update emitted to the score-updates topic and forwarded to Angular. */
case class ScoreUpdate(
  languageId:   Int,
  language:     String,
  subScoreType: String,
  delta:        Double,
  newScore:     Double,
  timestamp:    String,
)

object ScoreUpdate {
  implicit val encoder: Encoder[ScoreUpdate] = Encoder.instance { u =>
    import io.circe.syntax._
    io.circe.Json.obj(
      "language_id"    -> u.languageId.asJson,
      "language"       -> u.language.asJson,
      "sub_score_type" -> u.subScoreType.asJson,
      "delta"          -> u.delta.asJson,
      "new_score"      -> u.newScore.asJson,
      "timestamp"      -> u.timestamp.asJson,
    )
  }
}

/** Entry in the 30-day rolling window for one language. */
case class WindowEntry(timestampMs: Long, value: Double)
