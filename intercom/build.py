import re
import sys

source, out = sys.argv[1:]
s = open(source).read()

HEADER = """\
# Copy of https://github.com/intercom/Intercom-OpenAPI descriptions/2.14/api.intercom.io.yaml (MIT).
# Changes: the bearerAuth security scheme is declared as OAuth 2.0 with oauth2MetadataUrl (OpenAPI 3.2),
# and response schemas are corrected where api.intercom.io answers differently (checked 2026-11-24).
"""
BEARER = """\
      type: http
      scheme: bearer
"""
OAUTH = """\
      type: oauth2
      oauth2MetadataUrl: https://api.intercom.io/.well-known/oauth-authorization-server
      flows:
        authorizationCode:
          authorizationUrl: https://app.intercom.com/oauth
          tokenUrl: https://api.intercom.io/auth/eagle/token
          scopes: {}
"""
assert s.count(BEARER) == 1
s = s.replace(BEARER, OAUTH)


def block(name):
    m = re.search(r"^    %s:\n(?:(?:      .*|)\n)+" % re.escape(name), s, re.M)
    assert m, name
    return m.start(), m.end()

def edit(name, fn):
    global s
    a, b = block(name)
    new = fn(s[a:b])
    assert new != s[a:b], "no change in " + name
    s = s[:a] + new + s[b:]

def prop(text, key, fn):
    m = re.search(r"^        %s:\n(?:          .*\n)+" % re.escape(key), text, re.M)
    assert m, key
    new = fn(m.group(0))
    assert new != m.group(0), key
    return text[:m.start()] + new + text[m.end():]

def nullable(p):
    assert "nullable: true" not in p
    return re.sub(r"^(          type: \w+\n)", r"\1          nullable: true\n", p, count=1, flags=re.M)

def add_enum(value, after):
    def fn(p):
        assert ("          - %s\n" % after) in p, after
        return p.replace("          - %s\n" % after, "          - %s\n          - %s\n" % (after, value), 1)
    return fn

for name in ("conversation", "conversation_list_item"):
    edit(name, lambda t: prop(t, "priority", add_enum("none", "not_priority")))
stats = ["time_to_assignment", "time_to_admin_reply", "time_to_first_close", "time_to_last_close", "median_time_to_reply",
         "first_assignment_at", "first_admin_reply_at", "first_close_at", "last_assignment_at",
         "last_assignment_admin_reply_at", "last_admin_reply_at", "last_close_at", "last_closed_by_id", "handling_time"]
def fix_stats(t):
    for k in stats:
        t = prop(t, k, nullable)
    return t
edit("conversation_statistics", fix_stats)
edit("conversation_source", lambda t: prop(prop(t, "type", add_enum("messenger", "instagram")), "subject", nullable))
def nullable_ref(p):
    m = re.search(r'^          "?\$ref"?: (\S+)\n', p, re.M)
    assert m and "          nullable: true\n" in p
    p = p.replace("          nullable: true\n", "", 1)
    return p.replace(m.group(0), "          anyOf:\n          - \"$ref\": %s\n          - type: string\n            nullable: true\n            enum:\n            - null\n" % m.group(1), 1)
for name, key in [("admin_with_app", "app"), ("article", "statistics"), ("article_list_item", "translated_content"),
                  ("collection", "translated_content"), ("conversation_list_item", "ai_agent"), ("conversation", "ai_agent"),
                  ("conversation_part", "assigned_to"), ("conversation_part", "email_message_metadata"),
                  ("conversation_part", "metadata"), ("conversation_part", "event_details"),
                  ("create_collection_request", "translated_content"), ("ticket_part", "assigned_to"),
                  ("update_collection_request", "translated_content")]:
    edit(name, lambda t, key=key: prop(t, key, nullable_ref))
edit("custom_attributes", lambda t: t.replace("        - type: integer\n", "        - type: integer\n        - type: number\n        - type: boolean\n", 1))
edit("data_attribute", lambda t: prop(t, "data_type", add_enum("datetime", "date")))
edit("help_center", lambda t: prop(t, "display_name", nullable))
edit("internal_article_list_item", lambda t: prop(t, "id", lambda p: p.replace("          type: string\n", "          type: integer\n", 1).replace("example: '6871119'", "example: 6871119")))

m = re.search(r'(      - name: contact_id\n        in: path\n        required: true\n        description: [^\n]*\n        example: \'123\'\n        schema:\n          type: )integer(\n      tags:\n      - Notes\n      - Contacts\n      operationId: createNote\n)', s)
assert m, "createNote contact_id"
s = s[:m.start()] + m.group(1) + "string" + m.group(2) + s[m.end():]

open(out, "w").write(HEADER + s)
