# Icon

Details of an icon representing a `Device`. This page is a pilot for
model-driven tables: the table below is generated from
[`model/elements/Icon.yaml`](../../model/elements/Icon.yaml).

<!-- BEGIN GENERATED model:elements/Icon - do not edit; edit model/elements/Icon.yaml -->
| Name | Data Type | Description |
| --- | --- | --- |
| BitDepth (required) | integer | Bit depth of one color. |
| IconUsage | enumeration | Icon for the Device status. Any combination of values is allowed. Default value is: all values. Allowed values are from: DeviceStatus. |
| Size (required) | XYPair | Height and width of the icon in pixels. |
| FileSpec ? *(JDF 1.x only)* | element | Reference to details of the icon data. |
<!-- END GENERATED model:elements/Icon -->
