# Stage 1: cache sbt dependencies in a dedicated layer.
# This layer only rebuilds when build.sbt or project/ changes.
FROM eclipse-temurin:11-jdk-jammy AS deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://github.com/sbt/sbt/releases/download/v1.9.8/sbt-1.9.8.tgz \
    | tar xz -C /usr/local && \
    rm -rf /var/lib/apt/lists/*
ENV PATH="/usr/local/sbt/bin:${PATH}"
WORKDIR /app
COPY build.sbt .
COPY project/ project/
RUN sbt update

# Stage 2: compile and assemble fat jar.
FROM deps AS builder
COPY src/ src/
RUN sbt assembly && \
    mv target/scala-2.13/fossil-streaming-assembly-*.jar target/scala-2.13/fossil-streaming.jar

# Stage 3: minimal JRE runtime image.
FROM eclipse-temurin:11-jre-jammy AS runtime
WORKDIR /app
COPY --from=builder /app/target/scala-2.13/fossil-streaming.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
