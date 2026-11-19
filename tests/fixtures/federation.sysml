package Soc {
  part def Sensor {
  }

  part def Gateway {
  }

  part def Federation {
    part sensor : Sensor [3] {
      attribute site : Integer = 2;
      attribute application : Integer = 7;
      attribute entity : Integer = 100;
      attribute marking : String = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5100;
      attribute controlPort : Integer = 6100;
      attribute command : String = "sensor-agent";
      attribute cwd : String = "/opt/sensor";
    }

    part gateway : Gateway {
      attribute site : Integer = 1;
      attribute application : Integer = 9;
      attribute entity : Integer = 200;
      attribute marking : String = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5200;
      attribute controlPort : Integer = 6200;
      attribute command : String = "gateway";
      attribute cwd : String = "/opt/gateway";
    }
  }
}
