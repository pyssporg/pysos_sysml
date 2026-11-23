package PysosSoS {

  // Launch contract shared by every participant that is started for a run.
  //
  //   mode          how the participant is started
  //                 supervised | operator | manual
  //   readiness     what "started" means
  //                 none | port_bound | log_line
  //   timeout_s     bound on the readiness wait
  //   order         launch phase; lower starts first
  //   after_process process name or role that must be ready first;
  //                 empty means no dependency
  //
  // `after` is a SysML keyword, hence `after_process`. The vocabulary states
  // types only: values belong to the model that uses it.
  part def LaunchSpec {
    attribute mode : String;
    attribute readiness : String;
    attribute timeout_s : Real;
    attribute order : Integer;
    attribute after_process : String;
  }

  // The shape of a host-side application. Concrete processes specialize this
  // definition and supply `roles`, `command`, `cwd` and their own
  // `part launch : LaunchSpec` values; `effective_members` merges the base.
  part def Application {
    attribute roles : String;
    attribute command : String;
    attribute cwd : String;
    part launch : LaunchSpec;
  }
}
