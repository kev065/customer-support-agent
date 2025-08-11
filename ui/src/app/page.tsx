"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  return (
    <CopilotKit url="http://localhost:8000/chat">
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
