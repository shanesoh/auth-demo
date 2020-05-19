package httpapi.authz

default allow = false

# Only allow non-admin users to whoami
allow {
  input.method == "GET"
  input.path = ["whoami"]
  token.payload.preferred_username != "admin"
}

# By default endpoints are blocked. Explicitly allow following method+endpoint
allow {
  input.method == "POST"
  contains_element(input.path, "lookupSsn")
}

# Helper to get the token payload.
token = {"raw": input.token, "payload": payload} {
  [header, payload, signature] := io.jwt.decode(input.token)
}

# Helper to check if array contains element
contains_element(arr, elem) = true {
      arr[_] = elem
} else = false { true }
