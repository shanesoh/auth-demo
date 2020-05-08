package httpapi.authz

default allow = false

allow {
  input.method == "GET"
  input.path = ["whoami"]
  contains_element(token.payload.realm_access.roles, "k2o_owner")
}

# Helper to get the token payload.
token = {"payload": payload} {
  [header, payload, signature] := io.jwt.decode(input.token)
}

# Helper to check if array contains element
contains_element(arr, elem) = true {
      arr[_] = elem
} else = false { true }
