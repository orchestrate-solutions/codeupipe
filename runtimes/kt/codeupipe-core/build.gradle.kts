plugins {
    kotlin("jvm")
    `java-library`
    `maven-publish`
}

group = "com.codeupipe"
version = "0.1.0"

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    // Zero external dependencies — stdlib only
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            from(components["java"])
            artifactId = "codeupipe-core"
        }
    }
}
