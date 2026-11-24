import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
const req=createRequire(path.join(process.env.HOME,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json'));
const {FileBlob,PresentationFile}=await import(req.resolve('@oai/artifact-tool'));
const [source,out]=process.argv.slice(2);
const deck=await PresentationFile.importPptx(await FileBlob.load(source));
for(const [index,label] of ['cover','body'].entries()){
  const slide=deck.slides.items[Math.min(index,deck.slides.items.length-1)];
  const image=await deck.export({slide,format:'png',scale:1.25});
  await fs.writeFile(path.join(out,label+'.png'),new Uint8Array(await image.arrayBuffer()));
}
