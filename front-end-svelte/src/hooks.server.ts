import type { Handle, HandleServerError } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
  const authHeader = event.request.headers.get('authorization');
  if (authHeader?.startsWith('Nostr ')) {
    try {
      const payload = JSON.parse(atob(authHeader.slice(6)));
      event.locals.pubkey = payload.pubkey;
    } catch {
      // Header malformado — ignorar, no bloquear
    }
  }

  return resolve(event);
};

export const handleError: HandleServerError = async ({ error, status, message }) => {
  console.error(`[${status}]`, message, error);

  return {
    message: status === 404 ? 'Page not found' : 'An unexpected error occurred',
    code: `E${status}`,
  };
};
