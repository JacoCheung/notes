/* Local, illustrative Bernoulli model. No fitting or network requests. */
(() => {
  document.querySelectorAll(".dl-math").forEach(element => {
    if (window.katex) {
      katex.render(element.textContent, element, {
        displayMode: element.parentElement.classList.contains("dl-equation"),
        throwOnError: false,
      });
    }
  });

  const labs = [...document.querySelectorAll(".dl-lab")];
  const state = { free: true, meeting: false, prior: 40 };

  function render() {
    const spamLikelihood = (state.free ? 0.75 : 0.25) *
      (state.meeting ? 0.10 : 0.90);
    const hamLikelihood = (state.free ? 0.10 : 0.90) * 0.50;
    const prior = state.prior / 100;
    const spamScore = prior * spamLikelihood;
    const hamScore = (1 - prior) * hamLikelihood;
    const posterior = spamScore / (spamScore + hamScore);

    labs.forEach(lab => {
      const en = lab.dataset.language === "en";
      lab.querySelector('[data-input="free"]').checked = state.free;
      lab.querySelector('[data-input="meeting"]').checked = state.meeting;
      lab.querySelector('[data-input="prior"]').value = state.prior;
      const values = {
        prior: `${state.prior}%`,
        vector: `x = (${Number(state.free)}, ${Number(state.meeting)})`,
        "spam-likelihood": spamLikelihood.toFixed(4),
        "ham-likelihood": hamLikelihood.toFixed(4),
        "spam-prior": prior.toFixed(2),
        "ham-prior": (1 - prior).toFixed(2),
        "spam-score": spamScore.toFixed(4),
        "ham-score": hamScore.toFixed(4),
        posterior: `${en ? "Spam probability" : "垃圾邮件概率"} ${(posterior * 100).toFixed(1)}%`,
        calculation: `${spamScore.toFixed(4)} / (${spamScore.toFixed(4)} + ${hamScore.toFixed(4)})`,
        decision: posterior >= 0.5
          ? (en ? "At a 50% threshold: spam." : "按 50% 阈值：判为垃圾邮件。")
          : (en ? "At a 50% threshold: legitimate." : "按 50% 阈值：判为正常邮件。"),
      };
      Object.entries(values).forEach(([name, value]) => {
        lab.querySelectorAll(`[data-value="${name}"]`).forEach(element => {
          element.textContent = value;
        });
      });
      lab.querySelector(".dl-result-bar span").style.width = `${posterior * 100}%`;
    });
  }

  labs.forEach(lab => {
    lab.addEventListener("input", event => {
      const key = event.target.dataset.input;
      if (key === "prior") state.prior = Number(event.target.value);
      else if (key === "free" || key === "meeting") state[key] = event.target.checked;
      else return;
      render();
    });
    lab.querySelector("button").addEventListener("click", () => {
      Object.assign(state, { free: true, meeting: false, prior: 40 });
      render();
    });
  });
  render();
})();
