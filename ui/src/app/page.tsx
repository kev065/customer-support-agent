"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  // Provide both the public API key (for CopilotKit UI) and the runtimeUrl which
  // points to the backend CopilotKit endpoint mounted at /copilotkit.
  // Ensure runtimeUrl has a trailing slash to avoid a 307 redirect that some
  // browsers treat in ways that drop the response body.
  const rawRuntime = process.env.NEXT_PUBLIC_COPILOT_RUNTIME_URL || "";
  const runtimeUrl = rawRuntime.endsWith("/") ? rawRuntime : rawRuntime + "/";

  return (
    <CopilotKit
      publicApiKey={process.env.NEXT_PUBLIC_COPILOT_PUBLIC_API_KEY}
      runtimeUrl={runtimeUrl}
    >
      <CopilotPopup
        instructions="Welcome to the customer support agent! How can I help you today?"
        defaultOpen={true}
        labels={{
          title: "Customer Support Agent",
          initial: "Hi there! How can I help you?",
        }}
      />
    </CopilotKit>
  );
}
