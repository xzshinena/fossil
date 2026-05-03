ThisBuild / scalaVersion := "2.13.13"
ThisBuild / organization := "com.fossil"

lazy val root = project
  .in(file("."))
  .settings(
    name    := "fossil-streaming",
    version := "0.1.0",

    libraryDependencies ++= Seq(
      // ZIO
      "dev.zio" %% "zio"                         % "2.0.21",
      "dev.zio" %% "zio-streams"                 % "2.0.21",
      // ZIO ↔ Akka Streams interop via reactive streams
      "dev.zio" %% "zio-interop-reactivestreams" % "2.0.2",
      // Akka Streams (processing pipeline stage)
      "com.typesafe.akka" %% "akka-stream"        % "2.8.5",
      // GCP Pub/Sub
      "com.google.cloud"   % "google-cloud-pubsub" % "1.126.6",
      // JSON
      "io.circe" %% "circe-core"                  % "0.14.6",
      "io.circe" %% "circe-generic"               % "0.14.6",
      "io.circe" %% "circe-parser"                % "0.14.6",
      // Logging
      "ch.qos.logback"     % "logback-classic"     % "1.4.14",
    ),

    assembly / mainClass := Some("fossil.Main"),

    // Merge strategy for fat jar — reference.conf files must be concatenated,
    // not overwritten, so ZIO and Akka both get their defaults.
    assembly / assemblyMergeStrategy := {
      case PathList("META-INF", "MANIFEST.MF")  => MergeStrategy.discard
      case PathList("META-INF", "services", _*) => MergeStrategy.concat
      case PathList("META-INF", _*)             => MergeStrategy.discard
      case "reference.conf"                      => MergeStrategy.concat
      case "application.conf"                    => MergeStrategy.concat
      case _                                     => MergeStrategy.first
    },
  )
