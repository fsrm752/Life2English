/* Life2English · 界面交互逻辑
 *
 * 设计约束（与 SKILL.md 保持一致）：
 *   本文件**不实现任何业务逻辑**，只做两件事：
 *     1) 收集用户输入 → 通过 fetch('/api/<action>') 调用 skill_api 的 JSON 协议；
 *     2) 把返回的 JSON 渲染成 DOM。
 *   所有场景识别、任务生成、对话推进、反馈规则、总结，全部由后端 Python 负责，
 *   保证界面、CLI、智能体三条入口共用同一份实现，不存在第二套逻辑。
 */

(function () {
  "use strict";

  // -----------------------------------------------------------------------
  // 常量与状态
  // -----------------------------------------------------------------------

  var DONE_WORDS = ["done", "quit", "exit", "结束", "退出"];
  var REDO_WORDS = ["重答", "redo", "retry", "重新回答"];

  var state = {
    sceneId: null,
    sceneName: "",
    matchedKind: "strong",
    task: null,
    answers: [],          // 已提交的回答（用于 feedback / summary）
    dialogueDone: false,
    transferTask: null,
    transferAttempt: null,
    transferSkipped: false,
    busy: false,
  };

  var EL = {};

  // -----------------------------------------------------------------------
  // 协议调用
  // -----------------------------------------------------------------------

  // 本项目的官方在线部署地址：仅出现在「后端未连接」的提示文案中，
  // 用于指引用户改用正确入口；不作为任何资源加载来源（界面零外部依赖的原则不变）。
  var ONLINE_URL = "https://life2english.app.workbuddy.host/";

  // 后端未连接时的统一提示：讲清原因 + 给出可执行的下一步，
  // 避免出现「服务返回了非 JSON 内容」这类让人不知道怎么办的技术黑话。
  function disconnectedHint(status) {
    var mark = status ? "（HTTP " + status + "）" : "";
    return "无法连接后端服务" + mark + "——当前页面可能只是静态预览，后端并没有在运行。\n" +
      "请改用以下任一入口：\n" +
      "① 在线地址 " + ONLINE_URL + "\n" +
      "② 本地运行 python scripts/web_server.py 后访问 http://127.0.0.1:8770/";
  }

  function callApi(action, payload) {
    var body = Object.assign({ action: action }, payload || {});
    return fetch("/api/" + action, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).catch(function () {
      // 网络层失败：服务未启动 / 已停止 / 地址不可达
      throw new Error(disconnectedHint(0));
    }).then(function (resp) {
      return resp.text().then(function (text) {
        var data;
        try {
          data = JSON.parse(text);
        } catch (e) {
          // 非 JSON 响应：常见于「静态预览」场景（后端缺席时静态服务器返回 404 页面）
          throw new Error(disconnectedHint(resp.status));
        }
        if (!data || data.ok !== true) {
          throw new Error((data && data.error) || "未知错误");
        }
        return data;
      });
    });
  }

  // -----------------------------------------------------------------------
  // DOM 小工具
  // -----------------------------------------------------------------------

  function $(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) { node.className = cls; }
    if (text !== undefined && text !== null) { node.textContent = String(text); }
    return node;
  }

  function clear(node) {
    while (node.firstChild) { node.removeChild(node.firstChild); }
  }

  function show(node) { node.classList.remove("hidden"); }
  function hide(node) { node.classList.add("hidden"); }

  function setBusy(btn, busy, labelBusy, labelIdle) {
    if (!btn) { return; }
    btn.disabled = !!busy;
    if (labelBusy && labelIdle) {
      btn.textContent = busy ? labelBusy : labelIdle;
    }
  }

  function scrollInto(node) {
    if (node && node.scrollIntoView) {
      node.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  var SEV_LABEL = { issue: "问题", suggestion: "建议" };

  // -----------------------------------------------------------------------
  // ① 场景识别
  // -----------------------------------------------------------------------

  function renderExamples(scenes) {
    clear(EL.examples);
    scenes.slice(0, 4).forEach(function (s) {
      if (!s.example) { return; }
      var b = el("button", null, s.example);
      b.type = "button";
      b.addEventListener("click", function () {
        EL.sceneInput.value = s.example;
        EL.sceneInput.focus();
      });
      EL.examples.appendChild(b);
    });
  }

  function renderSceneList(scenes) {
    clear(EL.sceneList);
    scenes.forEach(function (s) {
      var item = el("div", "scene-item");
      item.appendChild(el("div", "name", s.name));
      var meta = s.name === s.id ? s.id : (s.id + " · " + s.difficulty);
      item.appendChild(el("div", "meta", meta));
      item.title = s.summary || "";
      item.addEventListener("click", function () {
        EL.sceneInput.value = s.example || s.name;
        startFromInput();
      });
      EL.sceneList.appendChild(item);
    });
  }

  function startFromInput() {
    var text = (EL.sceneInput.value || "").trim();
    if (!text) {
      EL.sceneInput.focus();
      return;
    }
    setBusy(EL.btnRecognize, true, "识别中…");
    callApi("recognize", { input: text }).then(function (data) {
      renderRecognize(data, text);
    }).catch(function (err) {
      renderRecognizeError(err.message);
    }).then(function () {
      setBusy(EL.btnRecognize, false, null, "开始学习");
    });
  }

  function renderRecognize(data, rawInput) {
    var box = EL.recognizeResult;
    clear(box);
    show(box);
    box.className = "recognize-result";

    if (data.kind === "none" || data.kind === "empty" || data.kind === "invalid" || !data.scene_id) {
      box.classList.add(data.kind === "none" ? "warn" : "bad");
      box.appendChild(el("div", "title", data.message || "暂时无法识别这个场景"));
      if (data.candidates && data.candidates.length) {
        box.appendChild(el("div", null, "你可以从下面最接近的场景开始："));
        var ul = el("ul", "cand-list");
        data.candidates.forEach(function (c) {
          var li = el("li");
          var left = el("div");
          left.appendChild(el("div", null, c.name));
          left.appendChild(el("div", "reason", c.reason || ""));
          li.appendChild(left);
          var btn = el("button", "primary", "选它");
          btn.type = "button";
          btn.addEventListener("click", function () {
            enterTask(c.scene_id, c.name, "picked");
          });
          li.appendChild(btn);
          ul.appendChild(li);
        });
        box.appendChild(ul);
      }
      return;
    }

    box.classList.add(data.kind === "strong" ? "ok" : "warn");
    var label = { strong: "完全匹配", weak: "部分匹配" }[data.kind] || data.kind;
    box.appendChild(el("div", "title", "已识别场景：" + data.scene_name + "（" + label + "）"));
    if (data.matched_keywords && data.matched_keywords.length) {
      box.appendChild(el("div", "reason", "命中关键词：" + data.matched_keywords.join("、")));
    }

    if (data.kind === "weak" && data.candidates && data.candidates.length) {
      box.appendChild(el("div", null, "这个输入也可能属于其它场景，确认一下："));
      var ul2 = el("ul", "cand-list");
      data.candidates.forEach(function (c) {
        var li = el("li");
        var left = el("div");
        left.appendChild(el("div", null, c.name));
        left.appendChild(el("div", "reason", c.reason || ""));
        li.appendChild(left);
        var btn = el("button", "ghost", "改用它");
        btn.type = "button";
        btn.addEventListener("click", function () {
          enterTask(c.scene_id, c.name, "picked");
        });
        li.appendChild(btn);
        ul2.appendChild(li);
      });
      box.appendChild(ul2);
    }

    enterTask(data.scene_id, data.scene_name, data.kind);
  }

  function renderRecognizeError(message) {
    var box = EL.recognizeResult;
    clear(box);
    show(box);
    box.className = "recognize-result bad";
    box.appendChild(el("div", "title", "调用失败"));
    box.appendChild(el("div", "reason", message));
  }

  // -----------------------------------------------------------------------
  // ② 学习任务
  // -----------------------------------------------------------------------

  function enterTask(sceneId, sceneName, matchedKind) {
    state.sceneId = sceneId;
    state.sceneName = sceneName || sceneId;
    state.matchedKind = matchedKind || "strong";
    resetLearningState();

    callApi("task", { scene_id: sceneId }).then(function (data) {
      state.task = data.task;
      renderTask(data.task);
      prepareDialogue();
    }).catch(function (err) {
      renderRecognizeError(err.message);
    });
  }

  function resetLearningState() {
    state.answers = [];
    state.dialogueDone = false;
    state.transferTask = null;
    state.transferAttempt = null;
    state.transferSkipped = false;
  }

  function renderTask(task) {
    EL.taskScene.textContent = task.scene_name + " · " + task.difficulty;
    EL.taskSituation.textContent = task.situation || "";
    hide(EL.taskSituation.parentNode);
    if (task.situation) { show(EL.taskSituation.parentNode); }
    EL.taskGoal.textContent = task.goal || "";

    clear(EL.exprList);
    (task.expressions || []).forEach(function (e) {
      var li = el("li");
      li.appendChild(el("div", "expr-en", e.en));
      li.appendChild(el("div", "expr-zh", e.zh));
      if (e.note) { li.appendChild(el("div", "expr-note", e.note)); }
      EL.exprList.appendChild(li);
    });
    EL.exprCount.textContent = "（" + (task.expressions || []).length + " 条）";

    EL.taskInteractive.textContent = task.interactive_task || "";

    clear(EL.taskNotes);
    (task.notes || []).forEach(function (n) {
      EL.taskNotes.appendChild(el("li", null, n));
    });
    if ((task.notes || []).length) { show(EL.notesBlock); } else { hide(EL.notesBlock); }

    clear(EL.taskMistakes);
    (task.common_mistakes || []).forEach(function (m) {
      EL.taskMistakes.appendChild(el("li", null, m));
    });
    if ((task.common_mistakes || []).length) { show(EL.mistakesBlock); } else { hide(EL.mistakesBlock); }

    show(EL.secTask);
    scrollInto(EL.secTask);
  }

  // -----------------------------------------------------------------------
  // ③ 情境互动
  // -----------------------------------------------------------------------

  function bubble(text, cls) {
    var d = el("div", "msg " + cls, text);
    EL.chat.appendChild(d);
    EL.chat.scrollTop = EL.chat.scrollHeight;
    return d;
  }

  function prepareDialogue() {
    clear(EL.chat);
    clear(EL.transferResult);
    hide(EL.transferResult);
    hide(EL.secFeedback);
    hide(EL.secTransfer);
    hide(EL.secSummary);
    show(EL.secDialogue);
    setBusy(EL.btnAnswer, true, null, null);

    callApi("interact", { scene_id: state.sceneId }).then(function (data) {
      EL.rolePill.textContent = data.role || "";
      if (data.opening) { bubble(data.opening, "bot"); }
      setBusy(EL.btnAnswer, false, null, null);
      EL.answerInput.value = "";
      EL.answerInput.focus();
      scrollInto(EL.secDialogue);
    }).catch(function (err) {
      bubble("加载开场失败：" + err.message, "sys");
    });
  }

  function sendAnswer() {
    if (state.busy || state.dialogueDone) { return; }
    var text = (EL.answerInput.value || "").trim();
    if (!text) { EL.answerInput.focus(); return; }

    var lower = text.toLowerCase();

    // 「重答」：撤回上一条回答（由 CLI 端的同一语义移植，本地仅做词汇判定，
    // 状态回退仍请求后端保持同步——此处因协议为无状态调用，直接在本地处理展示）
    if (REDO_WORDS.indexOf(lower) >= 0 || REDO_WORDS.indexOf(text) >= 0) {
      if (!state.answers.length) {
        bubble("还没有需要撤回的回答。", "sys");
        EL.answerInput.value = "";
        return;
      }
      state.answers.pop();
      var bubbles = EL.chat.querySelectorAll(".msg.me");
      if (bubbles.length) {
        EL.chat.removeChild(bubbles[bubbles.length - 1]);
      }
      bubble("已撤回上一条回答，请重新作答。", "sys");
      EL.answerInput.value = "";
      EL.answerInput.focus();
      return;
    }

    bubble(text, "me");
    EL.answerInput.value = "";

    if (DONE_WORDS.indexOf(lower) >= 0) {
      bubble("（你选择了结束互动）", "sys");
      finishDialogue();
      return;
    }

    state.answers.push(text);
    state.busy = true;
    setBusy(EL.btnAnswer, true, null, null);

    callApi("interact", { scene_id: state.sceneId, user_input: text }).then(function (data) {
      if (data.ack) { bubble(data.ack, "bot"); }
      if (data.done) {
        if (data.closing) { bubble(data.closing, "bot"); }
        var end = el("div", "msg sys", "互动结束，共 " + (data.rounds || 0) + " 轮。");
        EL.chat.appendChild(end);
        finishDialogue();
        return;
      }
      if (data.prompt) { bubble(data.prompt, "bot"); }
      if (data.hint) { bubble("提示：" + data.hint, "hint-msg"); }
    }).catch(function (err) {
      bubble("调用失败：" + err.message, "sys");
    }).then(function () {
      state.busy = false;
      setBusy(EL.btnAnswer, false, null, null);
      if (!state.dialogueDone) { EL.answerInput.focus(); }
    });
  }

  function finishDialogue() {
    state.dialogueDone = true;
    setBusy(EL.btnAnswer, true, null, null);
    setBusy(EL.btnDone, true, null, null);

    // ④ 表达反馈
    callApi("feedback", { scene_id: state.sceneId, answers: state.answers })
      .then(renderFeedback)
      .catch(function (err) {
        EL.feedbackBody.textContent = "生成反馈失败：" + err.message;
        show(EL.secFeedback);
      })
      .then(function () {
        // ⑤ 迁移练习
        return callApi("transfer", { scene_id: state.sceneId });
      })
      .then(function (data) {
        state.transferTask = data.task;
        renderTransfer(data.task);
      })
      .catch(function (err) {
        EL.transferPrompt.textContent = "生成迁移练习失败：" + err.message;
        show(EL.secTransfer);
      });
  }

  // -----------------------------------------------------------------------
  // ④ 表达反馈
  // -----------------------------------------------------------------------

  function renderFeedback(data) {
    var body = EL.feedbackBody;
    clear(body);

    (data.answers || []).forEach(function (fb) {
      var card = el("div", "fb-answer");
      card.appendChild(el("div", "quote", "“" + fb.answer + "”"));
      if (!fb.issues || !fb.issues.length) {
        card.appendChild(el("div", "no-issue", "未检测到问题（本地规则范围内）。"));
      } else {
        fb.issues.forEach(function (is) {
          var row = el("div", "fb-issue " + (is.severity === "issue" ? "issue" : "suggestion"));
          row.appendChild(el("span", "tag " + is.severity,
            "[" + (SEV_LABEL[is.severity] || is.severity) + "·" + is.kind + "]"));
          row.appendChild(el("span", null, is.quote + " → "));
          row.appendChild(el("span", "fix", is.fix));
          row.appendChild(el("div", "reason", is.reason));
          card.appendChild(row);
        });
      }
      body.appendChild(card);
    });

    if ((data.praises || []).length) {
      var p = el("div", "overall");
      p.appendChild(el("div", "praise", "做得好的地方"));
      var pul = el("ul");
      data.praises.forEach(function (x) { pul.appendChild(el("li", null, x)); });
      p.appendChild(pul);
      body.appendChild(p);
    }

    if (data.overall) {
      var ov = el("div", "overall");
      ov.appendChild(el("div", null, data.overall));
      body.appendChild(ov);
    }

    if (data.limitations) {
      body.appendChild(el("div", "limitations", "能力边界：" + data.limitations));
    }

    show(EL.secFeedback);
    scrollInto(EL.secFeedback);
  }

  // -----------------------------------------------------------------------
  // ⑤ 迁移练习
  // -----------------------------------------------------------------------

  function renderTransfer(task) {
    EL.transferScenario.textContent = task.scenario || "";
    EL.transferPrompt.textContent = task.prompt || "";
    if (task.example) {
      EL.transferExample.textContent = "参考：" + task.example;
      show(EL.transferExample);
    } else {
      hide(EL.transferExample);
    }
    EL.transferInput.value = "";
    setBusy(EL.btnTransfer, false, null, null);
    setBusy(EL.btnSkipTransfer, false, null, null);
    show(EL.secTransfer);
    scrollInto(EL.secTransfer);
  }

  function submitTransfer() {
    var text = (EL.transferInput.value || "").trim();
    if (!text) { EL.transferInput.focus(); return; }
    state.transferAttempt = text;
    state.transferSkipped = false;
    setBusy(EL.btnTransfer, true, "提交中…");

    callApi("transfer", { scene_id: state.sceneId, attempt: text }).then(function (data) {
      var r = data.result;
      var box = EL.transferResult;
      clear(box);
      show(box);
      box.className = "recognize-result ok";
      box.appendChild(el("div", "title", "迁移练习反馈"));
      var kw = (r.reused_keywords || []).length
        ? "复用到的关键词：" + r.reused_keywords.join("、")
        : "未复用本次学习的关键词。";
      box.appendChild(el("div", null, kw));
      if (r.note) { box.appendChild(el("div", "reason", r.note)); }
      renderSummary();
    }).catch(function (err) {
      var box = EL.transferResult;
      clear(box);
      show(box);
      box.className = "recognize-result bad";
      box.appendChild(el("div", null, "提交失败：" + err.message));
    }).then(function () {
      setBusy(EL.btnTransfer, false, null, "提交");
    });
  }

  function skipTransfer() {
    state.transferSkipped = true;
    state.transferAttempt = null;
    var box = EL.transferResult;
    clear(box);
    show(box);
    box.className = "recognize-result warn";
    box.appendChild(el("div", null, "已跳过迁移练习（总结中会如实标注）。"));
    renderSummary();
  }

  // -----------------------------------------------------------------------
  // ⑥ 学习总结
  // -----------------------------------------------------------------------

  function renderSummary() {
    var payload = {
      scene_id: state.sceneId,
      matched_kind: state.matchedKind,
      answers: state.answers
    };
    // 未作答时后端会视为"没有进行互动"，此处保持一致：
    // 只有确实提交过答案才让后端记录，避免虚构未发生的环节。
    if (state.transferSkipped) {
      payload.transfer_attempt = null;
    } else if (state.transferAttempt !== null) {
      payload.transfer_attempt = state.transferAttempt;
    }

    callApi("summary", payload).then(function (data) {
      var body = EL.summaryBody;
      clear(body);
      (data.sections || []).forEach(function (s) {
        var sec = el("div", "sum-section");
        sec.appendChild(el("h3", null, s.title));
        var ul = el("ul");
        (s.lines || []).forEach(function (line) {
          ul.appendChild(el("li", null, line));
        });
        sec.appendChild(ul);
        body.appendChild(sec);
      });
      if (data.closing_note) {
        body.appendChild(el("div", "closing-note", data.closing_note));
      }
      show(EL.secSummary);
      scrollInto(EL.secSummary);
    }).catch(function (err) {
      EL.summaryBody.textContent = "生成总结失败：" + err.message;
      show(EL.secSummary);
    });
  }

  // -----------------------------------------------------------------------
  // 重置 / 初始化
  // -----------------------------------------------------------------------

  function restart() {
    resetLearningState();
    state.sceneId = null;
    state.task = null;
    state.transferAttempt = null;
    hide(EL.secTask);
    hide(EL.secDialogue);
    hide(EL.secFeedback);
    hide(EL.secTransfer);
    hide(EL.secSummary);
    hide(EL.recognizeResult);
    clear(EL.transferResult);
    clear(EL.feedbackBody);
    clear(EL.summaryBody);
    clear(EL.chat);
    EL.sceneInput.value = "";
    EL.sceneInput.focus();
    scrollInto(EL.secInput);
  }

  function cacheDom() {
    EL.sceneInput = $("sceneInput");
    EL.btnRecognize = $("btnRecognize");
    EL.examples = $("examples");
    EL.recognizeResult = $("recognizeResult");

    EL.secInput = $("sec-input");
    EL.secTask = $("sec-task");
    EL.secDialogue = $("sec-dialogue");
    EL.secFeedback = $("sec-feedback");
    EL.secTransfer = $("sec-transfer");
    EL.secSummary = $("sec-summary");

    EL.taskScene = $("taskScene");
    EL.taskSituation = $("taskSituation");
    EL.taskGoal = $("taskGoal");
    EL.exprList = $("exprList");
    EL.exprCount = $("exprCount");
    EL.taskInteractive = $("taskInteractive");
    EL.taskNotes = $("taskNotes");
    EL.notesBlock = $("notesBlock");
    EL.taskMistakes = $("taskMistakes");
    EL.mistakesBlock = $("mistakesBlock");

    EL.rolePill = $("rolePill");
    EL.chat = $("chat");
    EL.answerInput = $("answerInput");
    EL.btnAnswer = $("btnAnswer");
    EL.btnDone = $("btnDone");

    EL.feedbackBody = $("feedbackBody");

    EL.transferScenario = $("transferScenario");
    EL.transferPrompt = $("transferPrompt");
    EL.transferExample = $("transferExample");
    EL.transferInput = $("transferInput");
    EL.btnTransfer = $("btnTransfer");
    EL.btnSkipTransfer = $("btnSkipTransfer");
    EL.transferResult = $("transferResult");

    EL.summaryBody = $("summaryBody");
    EL.btnRestart = $("btnRestart");
    EL.sceneList = $("sceneList");
    EL.versionBadge = $("versionBadge");
  }

  function bindEvents() {
    EL.btnRecognize.addEventListener("click", startFromInput);
    EL.sceneInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { startFromInput(); }
    });

    EL.btnAnswer.addEventListener("click", sendAnswer);
    EL.answerInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { sendAnswer(); }
    });
    EL.btnDone.addEventListener("click", function () {
      if (!state.dialogueDone) { finishDialogue(); }
    });

    EL.btnTransfer.addEventListener("click", submitTransfer);
    EL.transferInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { submitTransfer(); }
    });
    EL.btnSkipTransfer.addEventListener("click", skipTransfer);

    EL.btnRestart.addEventListener("click", restart);
  }

  function loadMeta() {
    fetch("/api/version").then(function (r) { return r.json(); }).then(function (v) {
      if (v && v.ok) {
        EL.versionBadge.textContent = "本地模拟版 v" + v.version + " · 不调用外部 API";
      }
    }).catch(function () { /* 版本信息非关键，失败静默 */ });

    fetch("/api/scenes").then(function (r) { return r.json(); }).then(function (d) {
      var scenes = (d && d.scenes) || [];
      renderExamples(scenes);
      renderSceneList(scenes);
    }).catch(function () {
      clear(EL.sceneList);
      EL.sceneList.appendChild(el("div", null, "场景列表加载失败：未连接后端服务。"));
      var jump = el("a", "scene-jump", "改用在线地址打开 →");
      jump.href = ONLINE_URL;
      jump.target = "_blank";
      jump.rel = "noopener";
      EL.sceneList.appendChild(jump);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    cacheDom();
    bindEvents();
    loadMeta();
  });
})();
