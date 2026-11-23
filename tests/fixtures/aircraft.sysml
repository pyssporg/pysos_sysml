package Aircraft {
  part def AircraftModel {
  }

  port def AircraftSignal {
    attribute gain : Real;
  }

  // Included roots are architecture: specialization, ports, and port defs are
  // accepted here even though the primary setup subset rejects them.
  part def AircraftDecoy :> AircraftModel {
    in port sig : AircraftSignal;
  }
}
