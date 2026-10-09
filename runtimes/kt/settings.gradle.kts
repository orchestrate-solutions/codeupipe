pluginManagement {
    plugins {
        kotlin("jvm") version "1.9.20"
    }
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
}

rootProject.name = "codeupipe-kt"
include("codeupipe-core")
