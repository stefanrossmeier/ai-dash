# Repository instructions

All commits must use `stefanrossmeier <github@rossmeier.info>` for both author and
committer. Configure this identity in the checkout before committing and verify it
before pushing. Do not use the inherited Issor identity.

AI Dash is an independent project. Its runtime, deployment, Windmill instance,
database, model gateway, model configuration, secrets and application state must
not depend on another project's checkout, services, volumes, network or CLI profile.
