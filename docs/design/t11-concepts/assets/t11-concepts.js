// T11 정적 시안 공통 상호작용
// 상태 전환 버튼과 AI 코치 오버레이 드래그를 처리합니다.
(() => {
  const switchers = document.querySelectorAll("[data-state-switcher]");

  switchers.forEach((switcher) => {
    const root = switcher.closest("[data-concept-root]");
    if (!root) return;

    const buttons = switcher.querySelectorAll("[data-state-target]");
    const panels = root.querySelectorAll("[data-state-panel]");

    const activate = (target) => {
      panels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.dataset.statePanel === target);
      });

      buttons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.stateTarget === target);
      });
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => activate(button.dataset.stateTarget));
    });
  });

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const makeDraggable = (target, handle) => {
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let startLeft = 0;
    let startTop = 0;
    let moved = false;

    const startDrag = (event) => {
      if (event.button !== undefined && event.button !== 0) return;

      const tablet = target.closest(".tablet");
      if (!tablet) return;

      const targetRect = target.getBoundingClientRect();
      const tabletRect = tablet.getBoundingClientRect();

      dragging = true;
      moved = false;
      startX = event.clientX;
      startY = event.clientY;
      startLeft = targetRect.left - tabletRect.left;
      startTop = targetRect.top - tabletRect.top;

      target.style.left = `${startLeft}px`;
      target.style.top = `${startTop}px`;
      target.style.right = "auto";
      target.style.bottom = "auto";
      target.style.position = "absolute";
      target.classList.add("is-dragging");
      target.style.setProperty("--drag-tilt", "0deg");

      handle.setPointerCapture?.(event.pointerId);
      event.preventDefault();
    };

    const moveDrag = (event) => {
      if (!dragging) return;

      const tablet = target.closest(".tablet");
      if (!tablet) return;

      const targetRect = target.getBoundingClientRect();
      const tabletRect = tablet.getBoundingClientRect();
      const nextLeft = startLeft + event.clientX - startX;
      const nextTop = startTop + event.clientY - startY;
      const maxLeft = tabletRect.width - targetRect.width - 8;
      const maxTop = tabletRect.height - targetRect.height - 8;

      if (Math.abs(event.clientX - startX) + Math.abs(event.clientY - startY) > 4) {
        moved = true;
      }

      target.style.left = `${clamp(nextLeft, 8, maxLeft)}px`;
      target.style.top = `${clamp(nextTop, 54, maxTop)}px`;
      target.style.setProperty("--drag-tilt", `${clamp((event.clientX - startX) / 18, -7, 7)}deg`);
    };

    const endDrag = (event) => {
      if (!dragging) return;
      dragging = false;
      handle.releasePointerCapture?.(event.pointerId);
      target.classList.remove("is-dragging");
      target.style.setProperty("--drag-tilt", "0deg");

      if (moved) {
        handle.dataset.dragMoved = "true";
        window.setTimeout(() => {
          delete handle.dataset.dragMoved;
        }, 0);
      }
    };

    handle.addEventListener("pointerdown", startDrag);
    handle.addEventListener("pointermove", moveDrag);
    handle.addEventListener("pointerup", endDrag);
    handle.addEventListener("pointercancel", endDrag);

    handle.addEventListener(
      "click",
      (event) => {
        if (handle.dataset.dragMoved) {
          event.preventDefault();
          event.stopPropagation();
        }
      },
      true,
    );
  };

  document.querySelectorAll(".coach-layer").forEach((layer) => {
    const handle = layer.querySelector(".coach-avatar");
    if (handle) makeDraggable(layer, handle);
  });

  document.querySelectorAll(".coach-idle").forEach((avatar) => {
    makeDraggable(avatar, avatar);
  });
})();
