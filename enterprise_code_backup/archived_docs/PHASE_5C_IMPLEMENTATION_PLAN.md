# Phase 5C: Production Deployment - Implementation Plan (CCW-v1.0)

## 1. Goal & Scope

### Goal
To finalize and deploy AICleaner v3 as a robust, production-ready, and optimized Home Assistant addon. This phase focuses on versioning, documentation, CI/CD automation, Docker optimization, and final validation to ensure a seamless user experience.

### Scope
The scope of this phase encompasses all activities required to transition the AICleaner v3 system from a development state to a distributable, production-grade application. This includes:
- **Versioning:** Implementing semantic versioning and automating changelog updates.
- **Documentation:** Finalizing all user-facing and developer documentation.
- **Containerization:** Optimizing the Docker image for size, security, and multi-architecture support.
- **CI/CD:** Creating a complete CI/CD pipeline for automated testing, building, and release management.
- **Testing:** Performing final integration, performance, and security validation.
- **Release:** Packaging the application for the Home Assistant addon store.

---

## 2. Task Decomposition

Phase 5C is broken down into the following discrete tasks:

1.  **Task 5C-1: Versioning and Changelog Management**
    -   Integrate a versioning tool (e.g., `bump2version`) to manage the project version.
    -   Establish the project's version in a central file (`build.yaml` or `config.yaml`).
    -   Automate `CHANGELOG.md` updates based on commit history or pull requests.

2.  **Task 5C-2: Documentation Finalization**
    -   Update `README.md` with comprehensive project overview, features, and usage examples.
    -   Create/Finalize `INSTALL.md` with detailed instructions for Home Assistant installation.
    -   Review and complete all documents in the `/docs` directory, ensuring consistency.
    -   Generate API documentation for key modules if applicable.

3.  **Task 5C-3: Docker Image Optimization**
    -   Refactor the `Dockerfile` to use multi-stage builds, drastically reducing the final image size.
    -   Implement multi-architecture builds for `amd64`, `arm64`, and `armv7` to support all common Home Assistant hardware.
    -   Harden the Docker image by removing unnecessary tools and running as a non-root user.

4.  **Task 5C-4: CI/CD Pipeline Implementation**
    -   Create a GitHub Actions workflow (`.github/workflows/release.yml`).
    -   The pipeline will trigger on pushes to `main` (for testing/linting) and on version tags (for releases).
    -   **Workflow Jobs:**
        -   `lint`: Check code formatting and quality.
        -   `unit-tests`: Run all unit tests.
        -   `build-and-push-docker`: Build and push multi-arch Docker images to a container registry (e.g., Docker Hub, GHCR).
        -   `create-github-release`: Automatically draft a new release on GitHub, using the changelog for release notes.

5.  **Task 5C-5: Production Validation Agent**
    -   Develop `phase5c_production_deployment_agent.py`.
    -   This agent will perform a final, end-to-end system validation within a containerized environment.
    -   Tests will include: HA integration checks, MQTT communication, UI endpoint availability, and final performance/resource benchmarks.
    -   Results will be logged to `phase5c_production_results.json`.

6.  **Task 5C-6: Release Preparation**
    -   Finalize the addon's `config.yaml` with the correct version, slug, and other metadata required by the Home Assistant addon store.
    -   Prepare the repository for public release (e.g., adding license, contribution guidelines).

---

## 3. Proposed Implementation Plan

### Technical Approach

1.  **Versioning:**
    -   We will use `bump2version` to manage version strings across `config.yaml`, `build.yaml`, and documentation files. The command `bump2version patch` will increment the version.
    -   The version will follow Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`). Initial release will be `1.0.0`.

2.  **Documentation:**
    -   `README.md`: Will be the main entry point for users.
    -   `INSTALL.md`: Will provide step-by-step instructions, including adding the repository to Home Assistant.
    -   `CHANGELOG.md`: Will be maintained using a tool like `git-cliff` or similar to generate structured logs from git history.

3.  **Docker Optimization:**
    -   **Multi-stage `Dockerfile`:**
        -   `build` stage: Use a full Python image to install dependencies from `requirements-full.txt`.
        -   `final` stage: Use a `python:3.12-slim` base image. Copy only the necessary application code and production dependencies from the `build` stage.
    -   **Multi-architecture Builds:**
        -   Utilize `docker buildx` within the GitHub Actions workflow to build for `linux/amd64`, `linux/arm64`, and `linux/arm/v7`.

4.  **CI/CD (GitHub Actions):**
    -   The `release.yml` workflow will use secrets for Docker registry login (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`).
    -   The workflow will tag Docker images with the Git tag (e.g., `v1.0.0`) and `latest`.

5.  **Production Validation:**
    -   The `phase5c_production_deployment_agent.py` will be executed as part of the CI/CD pipeline before the release step.
    -   It will use `docker-compose` to spin up the application and its dependencies (like an MQTT broker).
    -   It will run a series of `requests` and `paho-mqtt` checks to validate system health and integration points.

---

## 4. Implementation Strategy

### Files to Create:
-   `PHASE_5C_IMPLEMENTATION_PLAN.md` (this document)
-   `.github/workflows/release.yml` (CI/CD pipeline definition)
-   `phase5c_production_deployment_agent.py` (Final validation script)
-   `.bumpversion.cfg` (Configuration for the versioning tool)
-   `CONTRIBUTING.md`
-   `LICENSE`

### Files to Modify:
-   `Dockerfile`: Refactor for multi-stage builds.
-   `README.md`: Update with final content.
-   `INSTALL.md`: Update with final content.
-   `CHANGELOG.md`: Populate with all changes since the beginning of the project.
-   `config.yaml`: Finalize for Home Assistant addon store requirements, link version to `bumpversion`.
-   `requirements.txt`: Clean up to ensure only production dependencies are included.
-   `docker-compose.yml`: Update to use the production-optimized image and potentially add a testing service.

### Deployment Considerations:
-   **Registry:** A Docker Hub repository or GitHub Container Registry (GHCR) must be created to host the images.
-   **Secrets:** Repository secrets for the container registry must be configured in GitHub.
-   **Testing:** The production validation agent is a critical gate. A failing validation will prevent a release.
-   **Home Assistant:** The final `config.yaml` must be fully compliant with the Home Assistant addon specification to ensure it can be correctly installed and managed.