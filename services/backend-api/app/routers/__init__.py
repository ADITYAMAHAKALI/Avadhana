"""FastAPI routers, grouped by resource (auth, users, problems,
commitments, feed). Each router depends on service-layer functions via
`Depends()`, following the same interface/impl DI convention documented
in the repo README — routers never construct concrete repo/service
implementations inline.
"""
