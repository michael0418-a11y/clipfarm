const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = 3030;
const DATA_DIR = path.join(__dirname, 'data');
const LEADS_FILE = path.join(DATA_DIR, 'leads.json');
const SITES_DIR = path.join(__dirname, 'generated-sites');

fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(SITES_DIR, { recursive: true });
if (!fs.existsSync(LEADS_FILE)) fs.writeFileSync(LEADS_FILE, '[]');

const mime = { '.html':'text/html','.css':'text/css','.js':'application/javascript','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.ico':'image/x-icon','.svg':'image/svg+xml' };

function getLeads() { try { return JSON.parse(fs.readFileSync(LEADS_FILE,'utf8')); } catch { return []; } }
function saveLeads(l) { fs.writeFileSync(LEADS_FILE, JSON.stringify(l, null, 2)); }
function readBody(req) { return new Promise(res => { let b=''; req.on('data',c=>b+=c); req.on('end',()=>res(b)); }); }
function json(res, data, code=200) { res.writeHead(code,{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'}); res.end(JSON.stringify(data)); }
function cors(res) { res.setHeader('Access-Control-Allow-Origin','*'); res.setHeader('Access-Control-Allow-Methods','GET,POST,PATCH,DELETE,OPTIONS'); res.setHeader('Access-Control-Allow-Headers','Content-Type'); }
function serveFile(filePath, res) {
  const ext = path.extname(filePath).toLowerCase();
  try { const data = fs.readFileSync(filePath); res.writeHead(200,{'Content-Type':mime[ext]||'text/html'}); res.end(data); }
  catch { res.writeHead(404); res.end('Not found'); }
}

http.createServer(async (req, res) => {
  cors(res);
  if (req.method==='OPTIONS') { res.writeHead(204); res.end(); return; }
  const p = url.parse(req.url, true).pathname;
  const body = ['POST','PATCH','DELETE'].includes(req.method) ? await readBody(req) : '';
  let data;
  try { data = body ? JSON.parse(body) : {}; } catch { data = {}; }

  // GET leads
  if (p==='/api/leads' && req.method==='GET') return json(res, getLeads());

  // POST lead (add)
  if (p==='/api/leads' && req.method==='POST') {
    const leads = getLeads();
    const lead = { id: Date.now(), status:'new', notes:'', savedAt: new Date().toLocaleDateString(), siteSlug:null, ...data };
    leads.unshift(lead);
    saveLeads(leads);
    console.log('NEW LEAD:', lead.name, '-', lead.city);
    return json(res, { ok:true, lead });
  }

  // PATCH lead (update)
  if (p.startsWith('/api/leads/') && req.method==='PATCH') {
    const id = parseInt(p.split('/').pop());
    const leads = getLeads();
    const i = leads.findIndex(l=>l.id===id);
    if (i===-1) return json(res,{error:'not found'},404);
    leads[i] = { ...leads[i], ...data };
    saveLeads(leads);
    return json(res, { ok:true });
  }

  // DELETE lead
  if (p.startsWith('/api/leads/') && req.method==='DELETE') {
    const id = parseInt(p.split('/').pop());
    saveLeads(getLeads().filter(l=>l.id!==id));
    return json(res, { ok:true });
  }

  // POST save-site (save AI-generated HTML to disk)
  if (p==='/api/save-site' && req.method==='POST') {
    const { leadId, html, name } = data;
    const slug = (name||'site').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/-+$/,'')+'-'+Date.now();
    const siteDir = path.join(SITES_DIR, slug);
    fs.mkdirSync(siteDir, { recursive: true });
    fs.writeFileSync(path.join(siteDir,'index.html'), html);
    // Update lead with slug
    if (leadId) {
      const leads = getLeads();
      const i = leads.findIndex(l=>l.id===leadId);
      if (i!==-1) { leads[i].siteSlug = slug; leads[i].siteUrl = `http://localhost:${PORT}/sites/${slug}/`; saveLeads(leads); }
    }
    console.log('SITE SAVED:', slug);
    return json(res, { ok:true, slug, url:`http://localhost:${PORT}/sites/${slug}/` });
  }

  // Serve generated sites
  if (p.startsWith('/sites/')) {
    let fp = path.join(SITES_DIR, p.replace('/sites/',''));
    if (!path.extname(fp)) fp = path.join(fp,'index.html');
    if (!fp.startsWith(SITES_DIR)) { res.writeHead(403); res.end(); return; }
    return serveFile(fp, res);
  }

  // Serve dashboard
  if (p==='/' || p==='/dashboard') return serveFile(path.join(__dirname,'dashboard','index.html'), res);
  if (p.startsWith('/dashboard/')) return serveFile(path.join(__dirname,'dashboard',p.replace('/dashboard/','')), res);

  res.writeHead(404); res.end('Not found');

}).listen(PORT, () => {
  console.log('\n==========================================');
  console.log('  Web Agency Dashboard running!');
  console.log(`  Open: http://localhost:${PORT}`);
  console.log('==========================================\n');
});
