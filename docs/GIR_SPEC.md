# GIR Spec 0.1

GIR describes mathematical construction independently of visual coordinates. A scene has version, scene_type, objects, constraints, construction_steps and metadata. Objects include points, segments, lines, rays, circles, triangles, angles and labels. Constraints include membership, collinearity, perpendicularity, altitude, median and related primitives.

## Altitude example
A, B, C are points; BC is a segment; H belongs to BC; AH is perpendicular to BC; altitude is from A to BC through H.

## Median example
M is midpoint of BC; AM is the median from A to BC.

## Ambiguous case
“Проведите биссектрису” in triangle ABC is ambiguous until angle A, B or C is specified.


## Constraint target types
GIR 0.1 validation is structural and type-aware, but it is not a solver. It checks that constraint roles reference compatible object types:

- collinearity constraints target points;
- parallel and perpendicular constraints target line-like objects (`segment`, `line`, `ray`);
- segment and line endpoints, ray endpoints, triangle vertices and angle points must be distinct;
- collinearity and non-collinearity constraints target distinct points;
- midpoint and intersection constraints distinguish constructed points from carrier objects;
- altitude constraints target a source `point`, a line-like carrier (`segment`, `line`, `ray`), a foot `point` and an altitude `segment`;
- median constraints target a source `point`, a carrier `segment`, a midpoint `point` and a median `segment`;
- angle bisectors target an `angle` and a `ray`;
- circumcircle and incircle constraints target a `triangle` and a `circle`.

These checks prevent mathematically dirty GIR such as using a point where a circle is required, while still avoiding premature proof of constructibility.
