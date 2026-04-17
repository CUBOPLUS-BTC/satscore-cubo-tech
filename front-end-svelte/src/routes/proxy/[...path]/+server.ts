import { API_URL } from '$env/static/private';
import type { RequestHandler } from '@sveltejs/kit';

const handler: RequestHandler = async ({ params, request }) => {
  const url = `${API_URL}/${params.path}`;

  const headers = new Headers();
  const ct = request.headers.get('content-type');
  if (ct) headers.set('content-type', ct);
  const auth = request.headers.get('authorization');
  if (auth) headers.set('authorization', auth);

  const body = request.method !== 'GET' ? await request.text() : undefined;

  const res = await fetch(url, {
    method: request.method,
    headers,
    body,
  });

  const data = await res.text();

  return new Response(data, {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') ?? 'application/json' },
  });
};

export const GET = handler;
export const POST = handler;
