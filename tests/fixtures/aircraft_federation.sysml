package Flight {
  private import Aircraft::*;
  private import PysosSoS::*;

  part def AircraftEntity {
    part aircraft : AircraftModel;
  }

  part def Federation {
    part jet : AircraftEntity {
      attribute site : Integer = 3;
      attribute application : Integer = 4;
      attribute entity : Integer = 300;
      attribute marking : String = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5300;
      attribute controlPort : Integer = 6300;
      attribute command : String = "jet-engine";
      attribute cwd : String = "/opt/jet";
      attribute scenario : String = "cruise";
      part launch : LaunchSpec {
        attribute mode : String = "supervised";
        attribute readiness : String = "port_bound";
        attribute timeout_s : Real = 12.5;
        attribute order : Integer = 2;
        attribute after_process : String = "supervisor";
      }
    }
  }
}
