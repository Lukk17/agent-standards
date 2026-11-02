# Rename Checklist

Everything that names a module, a service or an image across a monorepo, in the order to walk it after a rename, and
the one cross-check that catches the drift nothing else reports. Load this file before renaming anything that has a
directory, a container or a scrape target, and again afterwards. The rules live in [SKILL.md](../SKILL.md).

---

### The cross-check that catches real drift

An IDE Docker build configuration names its image through `imageTag`. Compose names the same service's image through
its `image` line. Nothing keeps the two in step, so a project can reach a state where the IDE builds one name and
Compose expects another, someone rebuilds from the IDE, and nothing they did shows up in the running stack.

List both sides and compare.

```bash
grep -rn "imageTag" --include=*.run.xml .
```

```bash
grep -n "image:" docker-compose.yaml
```

This exact drift was found in a live repository: every run configuration built an unprefixed name such as
`inventory-api:latest`, while the compose file expected the project-prefixed `monorepo-inventory-api:latest` for the
same service. Add any additional compose files the stack loads to the second command, because a profile-gated
service is usually declared in one of those.

---

### Walk the list in order

One rename touched every item on this list, and the ones that were missed silently broke monitoring and two
end-to-end test prerequisites. Walk it in order, and grep for the old name after the last step.

1. The directory on disk.
2. The build tool's project name, `rootProject.name` in `settings.gradle.kts` or the equivalent, and the Spring
   application name in `application.yaml`, which is also the Eureka service id.
3. The module registration in `.idea/modules.xml` and the module file it points at, where the module is one the
   repository commits rather than one Gradle regenerates.
4. The run configurations, both their filenames and the paths inside them: `externalProjectPath`,
   `WORKING_DIRECTORY`, `SDK_HOME`, `sourceFilePath`, and every `<module name="...">`.
5. The IDE Docker run configurations: the `--name` inside `commandLineOptions` and the `imageTag`, checked against
   Compose with the cross-check above.
6. In Compose, three separate names that are easy to mistake for one: the service key under `services:`, the
   `container_name`, and the `image`. The build context and the Dockerfile path beside them.
7. The hostname other services resolve, in `extra_hosts`, in healthchecks and in every `base-url` property.
8. The Prometheus `job_name` and the `service` label on its static target, plus every Grafana dashboard query and
   every API-collection request that filters on `job="..."` or `service="..."`, because a scrape target renamed
   without its consumers leaves every panel empty and every collection assertion red.
9. The label the log pipeline attaches in its relabel rules, so log queries keep matching the service.
10. The gateway route id for the service, and any predicate or filter that names the old id.
11. Continuous integration paths, including the path filters that decide whether a job runs at all.
12. Documentation: every `AGENTS.md`, README, architecture document and decision record that names the old value,
    since a relative link to a renamed directory fails quietly in a rendered page.

---

### What was already renamed and what was not

The pattern of the misses is worth knowing, because it repeats. In the rename that produced this list, the Eureka
service id, the Spring application name, the container name and the image had all been renamed already, since each
of them is a value somebody reads on a running stack. The Compose service key and the Prometheus job and `service`
label had not, because both are addressed by tooling rather than read by a person: the key only matters to
`docker compose build <key>`, and the label only matters to a dashboard query. Grep for the old name across the
whole repository, including JSON dashboards and API collections, rather than trusting the list in your head.
