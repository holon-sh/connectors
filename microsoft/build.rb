require "yaml"
require "json"
require "set"

source, out = ARGV
GRAPH = YAML.unsafe_load_file(source)
APPS = YAML.load_file(File.join(__dir__, "apps.yaml"))
ORIGIN = "https://graph.microsoft.com/"
LOGIN = "https://login.microsoftonline.com/organizations"
HEADER = <<~TEXT
  # Cut from https://github.com/microsoftgraph/msgraph-metadata openapi/v1.0/openapi.yaml (MIT).
  # Changes: only the operations below are kept, the /v1.0 prefix moves from the server URL into each path, their names and summaries are rewritten, navigation properties,
  # discriminator maps, examples and the "@odata.type" requirement (Graph omits it in answers) are removed from schemas, and an OAuth 2.0 security scheme with oauth2MetadataUrl (OpenAPI 3.2) is added.
TEXT

def copy(value)
  Marshal.load(Marshal.dump(value))
end

def strip(value, schema: false)
  case value
  when Hash
    value.delete("examples") unless schema
    value.delete("externalDocs")
    value.delete("discriminator")
    if value["required"].is_a?(Array)
      value["required"] -= ["@odata.type"]
      value.delete("required") if value["required"].empty?
    end
    if value["properties"].is_a?(Hash)
      value["properties"].delete_if { |_, property| property.is_a?(Hash) && property["x-ms-navigationProperty"] == true }
    end
    value.each_value { |child| strip(child, schema: schema) }
  when Array
    value.each { |child| strip(child, schema: schema) }
  end
  value
end

def references(value, found)
  case value
  when Hash
    value.each { |key, child| key == "$ref" && child.is_a?(String) ? found << child : references(child, found) }
  when Array
    value.each { |child| references(child, found) }
  end
  found
end

APPS.each do |file, app|
  paths = {}
  app.fetch("operations").each do |name, operation|
    method, path = operation.fetch_values("method", "path")
    item = GRAPH.fetch("paths").fetch(path)
    target = (paths["/v1.0" + path] ||= {})
    target["parameters"] = copy(item["parameters"]) if item["parameters"] && !target.key?("parameters")
    target[method] = strip(copy(item.fetch(method))).merge(
      "operationId" => name, "summary" => operation.fetch("summary"), "description" => operation.fetch("summary"),
    ).except("tags")
  end
  components = {}
  queue = references(paths, [])
  seen = Set.new
  until queue.empty?
    reference = queue.shift
    next unless seen.add?(reference)
    _, _, kind, key = reference.split("/", 4)
    component = strip(copy(GRAPH.fetch("components").fetch(kind).fetch(key)), schema: kind == "schemas")
    (components[kind] ||= {})[key] = component
    references(component, queue)
  end
  scopes = app.fetch("scopes").to_h { |scope| [ORIGIN + scope, scope] }.merge("offline_access" => "offline_access")
  components["securitySchemes"] = {
    "microsoft" => {
      "type" => "oauth2",
      "oauth2MetadataUrl" => "#{LOGIN}/v2.0/.well-known/openid-configuration",
      "flows" => { "authorizationCode" => {
        "authorizationUrl" => "#{LOGIN}/oauth2/v2.0/authorize",
        "tokenUrl" => "#{LOGIN}/oauth2/v2.0/token",
        "scopes" => scopes,
      } },
    },
  }
  document = {
    "openapi" => GRAPH.fetch("openapi"),
    "info" => { "title" => app.fetch("title"), "version" => "v1.0", "description" => app.fetch("about") },
    "servers" => [{ "url" => ORIGIN.chomp("/") }],
    "security" => [{ "microsoft" => scopes.keys }],
    "paths" => paths,
    "components" => components.sort.to_h,
  }
  File.write(File.join(out, "#{file}.yaml"), HEADER + document.to_yaml)
end

items = APPS.map { |file, app| { "href" => "#{file}.yaml", "title" => app.fetch("name") } }
File.write(File.join(out, "microsoft.json"), JSON.pretty_generate("linkset" => [{ "item" => items }]) + "\n")
