# GIR Spec 0.1

GIR describes mathematical construction independently of visual coordinates. A scene has version, scene_type, objects, constraints, construction_steps and metadata. Objects include points, segments, lines, rays, circles, triangles, angles and labels. Constraints include membership, collinearity, perpendicularity, altitude, median and related primitives.

## Altitude example
A, B, C are points; BC is a segment; H belongs to BC; AH is perpendicular to BC; altitude is from A to BC through H.

## Median example
M is midpoint of BC; AM is the median from A to BC.

## Ambiguous case
“Проведите биссектрису” in triangle ABC is ambiguous until angle A, B or C is specified.
