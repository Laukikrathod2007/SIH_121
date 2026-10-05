(function () {
  function isolate() {
    var sticky = Array.from(document.querySelectorAll('[class~="lg:sticky"]'))
      .find(function (node) { return node.querySelector('.drilling-system-container') && node.textContent.includes('INTEGRATED SUBSURFACE VIEW'); });
    if (!sticky) return false;

    var section = sticky.closest('section');
    var grid = sticky.querySelector('.grid.grid-cols-12');
    var left = grid && grid.children[0];
    var heading = sticky.children[1];
    var figcaption = sticky.querySelector('.mt-3');
    if (!section || !grid || !left) return false;

    function keepOnlyChild(parent, child) {
      Array.from(parent.children).forEach(function (sibling) {
        if (sibling !== child) sibling.hidden = true;
      });
    }
    function keepBranch(root, leaf) {
      var node = leaf;
      while (node && node !== root) {
        var parent = node.parentElement;
        if (!parent) break;
        keepOnlyChild(parent, node);
        node = parent;
      }
    }

    keepBranch(document.body, section);
    keepBranch(section, sticky);
    keepOnlyChild(sticky, grid);
    if (heading) heading.hidden = false;
    if (figcaption) figcaption.hidden = false;

    var well = left.querySelector('.drilling-system-container');
    keepOnlyChild(left, well);
    keepOnlyChild(grid, left);
    grid.children[1].hidden = false;
    well.querySelectorAll('svg [fill], svg [stroke], svg [style]').forEach(function (node) {
      ['fill', 'stroke', 'style'].forEach(function (attribute) {
        var value = node.getAttribute(attribute);
        if (value) node.setAttribute(attribute, value.replace(/#22d3ee/gi, '#e87516').replace(/#67e8f9/gi, '#f5a45f'));
      });
    });

    section.style.cssText += ';display:block!important;min-height:0!important;padding:14px!important;margin:0!important;border:0!important;background:transparent!important;overflow:visible!important';
    sticky.style.cssText += ';position:static!important;inset:auto!important;width:100%!important;max-width:none!important;margin:0!important;padding:0!important';
    grid.style.cssText += ';display:grid!important;grid-template-columns:minmax(0,1.22fr) minmax(310px,.88fr);align-items:stretch!important;gap:14px!important;width:100%!important;margin:0!important';
    left.style.cssText += ';display:block!important;grid-column:1;grid-row:auto!important;width:100%!important;max-width:none!important;padding:0!important;margin:0!important';
    well.style.cssText += ';width:100%!important;max-width:none!important;margin:0!important';
    var logs = grid.children[1];
    logs.style.cssText += ';display:flex!important;grid-column:2;grid-row:auto!important;width:100%!important;max-width:none!important;min-width:0!important;margin:0!important;overflow:hidden!important';
    var outerGrid = grid.parentElement;
    var visualColumn = sticky.parentElement;
    if (outerGrid) outerGrid.style.cssText += ';display:block!important;grid-template-columns:minmax(0,1fr)!important;width:100%!important;max-width:none!important;margin:0!important';
    if (visualColumn) visualColumn.style.cssText += ';display:block!important;grid-column:1/-1!important;width:100%!important;max-width:none!important;margin:0!important;padding:0!important';
    var ancestor = sticky.parentElement;
    while (ancestor && ancestor !== section) {
      ancestor.style.width = '100%';
      ancestor.style.maxWidth = 'none';
      ancestor.style.marginLeft = '0';
      ancestor.style.marginRight = '0';
      ancestor.style.paddingLeft = '10px';
      ancestor.style.paddingRight = '10px';
      ancestor = ancestor.parentElement;
    }

    if (heading) {
      var labels = heading.querySelectorAll('span');
      if (labels[0]) labels[0].textContent = 'DRILLWISE / WELLBORE DIGITAL TWIN';
      if (labels[1]) labels[1].textContent = 'LIVE · SIMULATED';
    }
    if (figcaption) figcaption.textContent = 'DRILLWISE · REPRESENTATIVE WELLBORE + LWD / MWD';

    document.documentElement.classList.add('dw-petro-ready');
    document.documentElement.style.cssText += ';width:100%;height:auto;overflow:hidden;background:transparent';
    document.body.style.cssText += ';width:100%;height:auto;min-height:0;overflow:hidden;background:transparent';
    function syncHeight() {
      if (window.innerWidth <= 720) {
        grid.style.gridTemplateColumns = 'minmax(0,1fr)';
        logs.style.gridColumn = '1';
        left.style.gridColumn = '1';
      } else {
        grid.style.gridTemplateColumns = 'minmax(0,1.22fr) minmax(310px,.88fr)';
        logs.style.gridColumn = '2';
        left.style.gridColumn = '1';
      }
      if (window.frameElement) window.frameElement.style.height = Math.ceil(section.getBoundingClientRect().height + 30) + 'px';
    }
    syncHeight();
    window.addEventListener('resize', syncHeight);
    if (window.ResizeObserver) new ResizeObserver(syncHeight).observe(sticky);
    window.setTimeout(syncHeight, 250);
    window.setTimeout(syncHeight, 900);
    return true;
  }
  window.addEventListener('load', function () {
    var tries = 0;
    var timer = window.setInterval(function () {
      tries += 1;
      if (isolate() || tries > 40) window.clearInterval(timer);
    }, 100);
  }, { once: true });
})();
