package TwoInstances {
  part def Alpha {
  }

  part def Beta {
  }

  part def Federation {
    part alpha : Alpha {
      attribute site : Integer = 1;
      attribute application : Integer = 10;
      attribute entity : Integer = 1;
      attribute marking : String = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5551;
      attribute controlPort : Integer = 5651;
      attribute command : String = "alpha-engine --mode fast";
      attribute cwd : String = "/opt/alpha";
    }

    part beta : Beta {
      attribute site : Integer = 1;
      attribute application : Integer = 11;
      attribute entity : Integer = 2;
      attribute marking : String = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5552;
      attribute controlPort : Integer = 5652;
      attribute command : String = "beta-engine";
      attribute cwd : String = "/opt/beta";
    }
  }
}
