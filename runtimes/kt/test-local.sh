#!/bin/sh
# Run the Kotlin core's tests with kotlinc + JUnit 4, no Gradle.
#
# The Gradle build pins Kotlin plugin 1.9.20, which fails on Gradle 9.x, and
# its wrapper's Gradle 8.2 does not support recent JDKs. This compiles the
# same sources and tests with the installed kotlinc and runs them on JUnit.
# Needs: kotlinc (bundles kotlin-test), junit 4.13 + hamcrest in ~/.m2.
set -e
cd "$(dirname "$0")"
KLIB="$(dirname "$(readlink -f "$(command -v kotlinc)")")/../libexec/lib"
M2="${M2_REPO:-$HOME/.m2/repository}"
CP="$KLIB/kotlin-test.jar:$KLIB/kotlin-test-junit.jar:$M2/junit/junit/4.13.2/junit-4.13.2.jar:$M2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar"
OUT=build/local-test
mkdir -p "$OUT"
kotlinc -nowarn -cp "$CP" \
  codeupipe-core/src/main/kotlin/com/codeupipe/core/*.kt \
  codeupipe-core/src/test/kotlin/com/codeupipe/core/*.kt \
  -include-runtime -d "$OUT/tests.jar"
CLASSES=$(cd codeupipe-core/src/test/kotlin && ls com/codeupipe/core/*.kt | sed 's/\.kt$//; s#/#.#g')
exec java -cp "$OUT/tests.jar:$CP" org.junit.runner.JUnitCore $CLASSES
