# Snout.pink

A subscription tracking application with passkey authentication. Track your recurring subscriptions, visualize spending with interactive treemaps, and manage your services in one place.

## Features

- **Passkey Authentication** - Passwordless login using WebAuthn/FIDO2
- **Subscription Management** - Track all your recurring subscriptions
- **Treemap Visualization** - See your spending distribution with D3.js
- **Multi-Currency Support** - Track subscriptions in different currencies
- **Mobile-First Design** - Built with Ionic for a responsive experience

## Tech Stack

**Frontend:** Angular 20, Ionic 8, D3.js, TypeScript
**Backend:** FastAPI, Python 3.14+, MongoDB, Beanie ODM
**Infrastructure:** Docker, Caddy, Let's Encrypt

## Development

```bash
# Install dependencies
just install

# Run backend
just backend

# Run frontend
just frontend

# Run full stack with Docker
just up
```

## Acknowledgments

This project was inspired by [SubGrid](https://github.com/hoangvu12/subgrid) by [@hoangvu12](https://github.com/hoangvu12) - a subscription visualization tool that displays monthly costs in an interactive treemap format.

## License

[MIT](LICENSE)
