# Requires a running Podman default machine. Does not alter existing containers.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'env.ps1')
if (-not $env:POSTGRES_PASSWORD) { throw 'POSTGRES_PASSWORD missing from .env' }
$env:POSTGRES_USER = 'advergent'
$env:POSTGRES_DB = 'advergent'
podman run --detach --name advergent-postgres --publish 127.0.0.1:5432:5432 --env POSTGRES_USER --env POSTGRES_DB --env POSTGRES_PASSWORD --volume advergent-operational:/var/lib/postgresql/data docker.io/library/postgres:17.9-alpine
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL container did not start; inspect existing container before retrying' }
