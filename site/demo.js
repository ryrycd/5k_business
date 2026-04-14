const chatLog = document.getElementById("chat-log");
const chatChoices = document.getElementById("chat-choices");
const leadPayload = document.getElementById("lead-payload");
const resetButton = document.getElementById("reset-chat");

const steps = [
  {
    key: "service",
    bot: "Hi, I can help you get a roofing estimate quickly. What do you need help with?",
    choices: [
      { label: "Roof leak", value: "Roof leak" },
      { label: "Storm damage", value: "Storm damage" },
      { label: "Full replacement", value: "Full replacement" },
    ],
  },
  {
    key: "timeline",
    bot: "How soon do you want to be contacted?",
    choices: [
      { label: "ASAP", value: "ASAP" },
      { label: "This week", value: "This week" },
      { label: "Just pricing for now", value: "Pricing research" },
    ],
  },
  {
    key: "ownership",
    bot: "Is this for a home you own or manage?",
    choices: [
      { label: "Own", value: "Owner" },
      { label: "Manage", value: "Property manager" },
      { label: "Commercial", value: "Commercial contact" },
    ],
  },
  {
    key: "insurance",
    bot: "Is insurance involved?",
    choices: [
      { label: "Yes", value: "Insurance claim likely" },
      { label: "No", value: "Private pay" },
      { label: "Not sure", value: "Unknown" },
    ],
  },
  {
    key: "callback",
    bot: "Perfect. Last question: what callback method should we use?",
    choices: [
      { label: "Call me", value: "Phone callback" },
      { label: "Text me", value: "SMS callback" },
      { label: "Email me", value: "Email callback" },
    ],
  },
];

let currentStep = 0;
let answers = {};

function renderPayload() {
  leadPayload.innerHTML = `
    <div class="payload-row">
      <span>Status</span>
      <strong>${currentStep === steps.length ? "Qualified lead ready for owner alert" : "Collecting details"}</strong>
    </div>
    <div class="payload-row">
      <span>Service</span>
      <strong>${answers.service || "Pending"}</strong>
    </div>
    <div class="payload-row">
      <span>Timeline</span>
      <strong>${answers.timeline || "Pending"}</strong>
    </div>
    <div class="payload-row">
      <span>Ownership</span>
      <strong>${answers.ownership || "Pending"}</strong>
    </div>
    <div class="payload-row">
      <span>Insurance</span>
      <strong>${answers.insurance || "Pending"}</strong>
    </div>
    <div class="payload-row">
      <span>Preferred callback</span>
      <strong>${answers.callback || "Pending"}</strong>
    </div>
    <div class="payload-note">
      Owner alert: "New roofing lead marked ${answers.timeline || "pending"} with ${answers.service || "unknown job"}."
    </div>
  `;
}

function appendBubble(text, type = "bot") {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${type}`;
  bubble.textContent = text;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderChoices(step) {
  chatChoices.innerHTML = "";
  step.choices.forEach((choice) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-button";
    button.textContent = choice.label;
    button.addEventListener("click", () => {
      answers[step.key] = choice.value;
      appendBubble(choice.label, "user");
      currentStep += 1;
      renderPayload();
      if (currentStep < steps.length) {
        window.setTimeout(() => {
          appendBubble(steps[currentStep].bot, "bot");
          renderChoices(steps[currentStep]);
        }, 300);
      } else {
        window.setTimeout(() => {
          appendBubble(
            "Thanks. I have enough to notify the owner and route this for a fast estimate follow-up.",
            "bot"
          );
          chatChoices.innerHTML = '<a class="button primary full-width" href="mailto:you@yourdomain.com">Use this demo in outreach</a>';
          renderPayload();
        }, 300);
      }
    });
    chatChoices.appendChild(button);
  });
}

function resetDemo() {
  currentStep = 0;
  answers = {};
  chatLog.innerHTML = "";
  appendBubble(steps[0].bot, "bot");
  renderChoices(steps[0]);
  renderPayload();
}

resetButton.addEventListener("click", resetDemo);
resetDemo();
