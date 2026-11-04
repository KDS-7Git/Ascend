export default { async fetch(request) { const p=new URL(request.url).pathname; return Response.json(p==="/version"?{release:"worker-v1"}:{status:"ready",storage:"none"}); } };
