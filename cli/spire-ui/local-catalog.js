import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const categories = new Set(['cards', 'monsters', 'relics', 'potions', 'characters']);
const cached = new Map();
const freeze = value => {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
};
async function read(name, expectedHash) {
  if (!cached.has(name)) {
    const loading = (async () => {
      try {
        const bytes = await readFile(new URL(`./catalog-data/${name}.json`, import.meta.url));
        if (expectedHash && createHash('sha256').update(bytes).digest('hex') !== expectedHash) throw new Error('checksum');
        const data = JSON.parse(bytes.toString('utf8'));
        if (data.schemaVersion !== 1) throw new Error('schema');
        return freeze(data);
      } catch { throw new Error('本地资料库缺失或损坏，请更新或重新安装 Spire 扩展。'); }
    })();
    cached.set(name, loading);
    loading.catch(() => { if (cached.get(name) === loading) cached.delete(name); });
  }
  return cached.get(name);
}
async function metadata() { return read('metadata'); }
async function categoryData(category) {
  if (!categories.has(category)) throw new Error('未知资料分类');
  const meta = await metadata(), hash = meta.files?.[`${category}.json`];
  if (!/^[a-f0-9]{64}$/.test(hash ?? '')) throw new Error('本地资料库版本无效，请更新 Spire 扩展。');
  const data = await read(category, hash);
  if (data.category !== category || data.version !== meta.version || data.items.length !== meta.categories.find(row => row.id === category)?.count) throw new Error('本地资料库版本不一致，请更新 Spire 扩展。');
  return data;
}
async function list(category, group = '') {
  const data = await categoryData(category);
  const items = group ? data.items.filter(row => row.group === group) : data.items;
  return { items, total: items.length, groups: data.groups, version: data.version };
}
async function detail(category, id, { ascension = 0, upgraded = false } = {}) {
  const data = await categoryData(category);
  if (!Object.hasOwn(data.details, id)) throw new Error('资料条目不存在');
  const variants = data.details[id];
  if (category === 'monsters') {
    if (!Number.isInteger(ascension) || ascension < 0 || ascension >= variants.ascensions.length) throw new Error('无效的进阶等级');
    return variants.ascensions[ascension];
  }
  return category === 'cards' && upgraded ? variants.upgraded : variants.base;
}
export const localCatalog = Object.freeze({ metadata, list, detail });
