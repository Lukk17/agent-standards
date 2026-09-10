# Run Configurations

The XML the IDE actually honours for each kind of run configuration, read out of live `.run/` directories rather
than reconstructed from the dialog. Load this file when creating or repairing one, or when one shows up under an
Unknown category or with an empty interpreter field. The rules live in [SKILL.md](../SKILL.md).

---

### Where the files live

A run configuration is one XML file per configuration, named after the configuration with a `.run.xml` suffix,
either in the project root under `.run/` or in a module under its own `.run/` directory. Every file wraps a single
`configuration` element in a `ProjectRunConfigurationManager` component. Module-scoped files keep the configuration
next to the code it runs, which is what a monorepo wants, and they still appear in one flat run menu.

Paths inside these files use the `$PROJECT_DIR$` macro so the file survives a clone into a different directory. A
literal absolute path works on the machine that wrote it and nowhere else.

---

### How to get an option name right

The platform matches each option name against the ones it knows and silently drops the rest, so an invented name is
never caught by anything. Two routes are reliable, and there is no third.

1. Copy a working configuration of the same type produced by the same IDE version, and change only the values.
2. Create the configuration once through the IDE dialog, save it to the project through the Store as project file
   toggle, and read the XML the IDE wrote under `.run/`.

The Unknown label in the run menu is the visible symptom of an unrecognised `type` value. An unrecognised option
name inside a recognised type has no symptom at all, which is why the guessing has to stop before the file is saved.

---

### Docker Compose deploy

The type is `docker-deploy` and the `factoryName` is `docker-compose.yml`. The `server-name` value is the name of the
Docker connection registered in the IDE, normally `Docker`.

```xml
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="compose [rebuild recreate]" type="docker-deploy" factoryName="docker-compose.yml" server-name="Docker">
    <deployment type="docker-compose.yml">
      <settings>
        <option name="composeProjectName" value="pharmacy" />
        <option name="commandLineOptions" value="--build" />
        <option name="sourceFilePath" value="docker-compose.yaml" />
        <option name="upForceRecreate" value="true" />
      </settings>
    </deployment>
    <method v="2" />
  </configuration>
</component>
```

`sourceFilePath` is the compose file relative to the project root, and `composeProjectName` is the `-p` value, so the
IDE and the command line address one stack. The trap is that flags reach `docker compose` through two mechanisms
that look alike in the dialog. `commandLineOptions` is free text appended to the command, and `--build` travels that
way. Force recreate is not a command line flag in this model, it is a separate boolean option named
`upForceRecreate`. Writing `--force-recreate` into `commandLineOptions` produces a configuration that behaves exactly
like the plain one, which is the failure that happened.

A `services` option holding a list of service names narrows the run to part of the stack instead of bringing up
everything the file declares.

---

### Docker image build and run

Same `docker-deploy` type, `factoryName` `dockerfile`. `sourceFilePath` points at the Dockerfile rather than a
compose file, `imageTag` names the image that gets built, and `buildOnly` set to `true` builds without starting a
container.

```xml
<configuration default="false" name="inventory-api Build" type="docker-deploy" factoryName="dockerfile" server-name="Docker">
  <deployment type="dockerfile">
    <settings>
      <option name="imageTag" value="inventory-api:latest" />
      <option name="buildOnly" value="true" />
      <option name="sourceFilePath" value="apps/inventory-api/Dockerfile" />
    </settings>
  </deployment>
  <method v="2" />
</configuration>
```

Drop `buildOnly` and the same shape runs the container. A run variant adds `containerName`, an `envVars` option
holding a list of `DockerEnvVarImpl` entries with `name` and `value` children, and a `portBindings` option holding
`DockerPortBindingImpl` entries with `containerPort` and `hostPort`. A value that is a secret belongs in
`commandLineOptions` as a bare `--env NAME`, so the value comes from the surrounding environment rather than being
written into a tracked file.

The `imageTag` here and the `image` line in Compose for the same service are kept in step by nothing. The cross-check
is in [rename-checklist.md](rename-checklist.md).

---

### Python

The type is `PythonConfigurationType` with `factoryName` `Python`. To run an installed module such as `uvicorn`
rather than a script file, set `MODULE_MODE` to `true` and put the module name in `SCRIPT_NAME`, with its arguments
in `PARAMETERS`. `WORKING_DIRECTORY` is the module root, not its `src` directory, because the application is imported
as `src.main` and that import has to resolve from the root.

```xml
<configuration default="false" name="inventory-api uvicorn" type="PythonConfigurationType" factoryName="Python">
  <module name="monorepo" />
  <option name="SDK_HOME" value="$PROJECT_DIR$/apps/inventory-api/.venv/Scripts/python.exe" />
  <option name="SDK_NAME" value="D:\Development\monorepo\apps\inventory-api\.venv" />
  <option name="IS_MODULE_SDK" value="false" />
  <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$/apps/inventory-api" />
  <option name="MODULE_MODE" value="true" />
  <option name="SCRIPT_NAME" value="uvicorn" />
  <option name="PARAMETERS" value="src.main:app --host 0.0.0.0 --port 7020 --reload" />
</configuration>
```

The interpreter needs both halves, and this is the part people get wrong. `SDK_HOME` is the path, written relative to
the project so the file stays portable. `SDK_NAME` is the name under which the IDE registered that interpreter in its
own table, and `IS_MODULE_SDK` set to `false` says the configuration carries its own interpreter instead of
inheriting the module's. Supply `SDK_HOME` alone and the interpreter field in the dialog comes up empty, because the
IDE only offers interpreters it has already registered. Supply `SDK_NAME` alone and the file stops being portable.

Be honest about the consequence when handing this over. The file travels with the repository and carries the right
paths and arguments, and each machine still has to register its own interpreter once through the IDE before the
configuration resolves. The registry it lands in is described in [windows-traps.md](windows-traps.md).

---

### Gradle

The type is `GradleRunConfiguration` with `factoryName` `Gradle`. `externalProjectPath` points at the directory that
owns the build, and `taskNames` holds a list of tasks executed in order.

```xml
<configuration default="false" name="inventory-api clean build" type="GradleRunConfiguration" factoryName="Gradle">
  <ExternalSystemSettings>
    <option name="externalProjectPath" value="$PROJECT_DIR$/apps/inventory-api" />
    <option name="externalSystemIdString" value="GRADLE" />
    <option name="taskNames">
      <list>
        <option value="clean" />
        <option value="build" />
      </list>
    </option>
  </ExternalSystemSettings>
  <method v="2" />
</configuration>
```

Two configurations per Java module is a good default: one that runs the application, usually `bootRun` with a
`--args='--spring.profiles.active=<profile>'` entry in the same list, and one that does `clean build`.

---

### Spring Boot

The type is `SpringBootApplicationConfigurationType` with `factoryName` `Spring Boot`. Unlike the Gradle form, it
runs the application from the IDE's own module model, so it carries a `module` element naming the IDE module that
holds the main class.

```xml
<configuration default="false" name="PharmacyApplication local" type="SpringBootApplicationConfigurationType" factoryName="Spring Boot">
  <option name="ACTIVE_PROFILES" value="local" />
  <module name="pha-pharma.pha-pharma-app" />
  <option name="SPRING_BOOT_MAIN_CLASS" value="com.revdevs.pharmacy.PharmacyApplication" />
  <method v="2">
    <option name="Make" enabled="true" />
  </method>
</configuration>
```

That `module` name is the fragile part. It has to match a module the IDE currently shows, and the module names change
when the Gradle import switches between one module per source set and one per project, which is decided in
`.idea/gradle.xml` and described in [gradle-monorepo.md](gradle-monorepo.md). A configuration pinned to
`pha-pharma.pha-pharma-app.main` breaks silently the day that module stops existing, and only the configurations the
IDE happened to have open are rewritten by it. Grep the rest.

```bash
grep -rn "<module name=" --include=*.run.xml .
```

---

### Shell script

The type is `ShConfigurationType`. `ShellScriptRunConfigurationType` does not exist, and a configuration naming it
lands in the run menu under an Unknown category with no way to launch it. That Unknown label is the visible symptom
of any unrecognised `type` value, not only this one.
