import type { paths } from "./generated/geometryos";

type GenerateRequest = paths["/api/v1/generate"]["post"]["requestBody"]["content"]["application/json"];
type GenerateResponse = paths["/api/v1/generate"]["post"]["responses"][200]["content"]["application/json"];
type GenerateUnavailable = paths["/api/v1/generate"]["post"]["responses"][503]["content"]["application/problem+json"];
type GenerateTimeout = paths["/api/v1/generate"]["post"]["responses"][504]["content"]["application/problem+json"];
type SvgResponse = paths["/api/v1/render/svg"]["post"]["responses"][200]["content"]["application/json"];
type ReadyResponse = paths["/ready"]["get"]["responses"][200]["content"]["application/json"];
type NotReadyResponse = paths["/ready"]["get"]["responses"][503]["content"]["application/json"];

const request: GenerateRequest = {
  input_type: "text",
  input: "Постройте треугольник ABC и проведите высоту.",
  output: ["svg"],
  mode: "strict",
};

function handleGenerateResponse(response: GenerateResponse): string | null {
  switch (response.status) {
    case "success":
      return response.gir.schema_version;
    case "needs_clarification":
      return response.ambiguities?.[0]?.code ?? null;
    case "error":
      return response.warnings?.[0]?.code ?? null;
    default: {
      const exhaustive: never = response;
      return exhaustive;
    }
  }
}

const svgMediaType: SvgResponse["media_type"] = "image/svg+xml";
const unavailableCode: GenerateUnavailable["code"] = "service_unavailable";
const timeoutCode: GenerateTimeout["code"] = "operation_timeout";
const readiness: ReadyResponse["status"] = "ready";
const notReadiness: NotReadyResponse["status"] = "not_ready";

void request;
void handleGenerateResponse;
void svgMediaType;
void unavailableCode;
void timeoutCode;
void readiness;
void notReadiness;
