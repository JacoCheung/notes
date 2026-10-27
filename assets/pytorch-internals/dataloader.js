(() => {
  'use strict';
  document.querySelectorAll('.loader-figure').forEach(figure => {
    const svg=figure.querySelector('svg');
    figure.querySelectorAll('[data-fit]').forEach(button => {
      button.addEventListener('click', () => {
        svg.style.width=button.dataset.fit==='fit'?'100%':svg.viewBox.baseVal.width+'px';
        figure.querySelectorAll('[data-fit]').forEach(item => item.setAttribute('aria-pressed',String(item===button)));
      });
    });
  });
  document.querySelectorAll('.loader-lab').forEach(lab => {
    const en=lab.dataset.lang==='en';
    const update=() => {
      const order=[3,0,4,1,2];
      const ranks=Number(lab.querySelector('[data-ranks]').value);
      const batch=Number(lab.querySelector('[data-batch]').value);
      const samplerDrop=lab.querySelector('[data-sampler-drop]').checked;
      const batchDrop=lab.querySelector('[data-batch-drop]').checked;
      const localSize=(samplerDrop?Math.floor:Math.ceil)(order.length/ranks);
      const total=localSize*ranks;
      const slots=Array.from({length:total},(_,i)=>({value:order[i%order.length],pad:i>=order.length}));
      lab.querySelector('[data-global]').textContent='['+slots.map(s=>s.value+(s.pad?'*':'')).join(', ')+']';
      const body=lab.querySelector('tbody'); body.replaceChildren();
      let used=0; const unique=new Set();
      const format=items=>'['+items.map(s=>s.value+(s.pad?'*':'')).join(', ')+']';
      for(let rank=0;rank<ranks;rank++){
        const local=slots.filter((_,i)=>i%ranks===rank);
        const batches=[]; const dropped=[];
        for(let i=0;i<local.length;i+=batch){
          const part=local.slice(i,i+batch);
          if(batchDrop&&part.length<batch){dropped.push(...part);continue;}
          batches.push(format(part));used+=part.length;part.forEach(s=>unique.add(s.value));
        }
        const row=document.createElement('tr');
        [String(rank),format(local),batches.join(' · ')||(en?'No batch':'无 batch'),format(dropped)].forEach(value=>{
          const cell=document.createElement('td');cell.textContent=value;row.append(cell);
        });
        body.append(row);
      }
      lab.querySelector('[data-summary]').textContent=en
        ?`Sampler: ${total-order.length>=0?total-order.length+' padded slots':order.length-total+' dropped indices'}. DataLoader outputs ${used} sample slots covering ${unique.size} unique samples. * marks an added copy, not a new sample.`
        :`Sampler：${total-order.length>=0?'补齐 '+(total-order.length)+' 个位置':'丢弃 '+(order.length-total)+' 个索引'}。DataLoader 最终输出 ${used} 个样本位置，覆盖 ${unique.size} 个不同样本。* 表示补入的重复项，不是新样本。`;
    };
    lab.addEventListener('change',update);update();
  });
})();
