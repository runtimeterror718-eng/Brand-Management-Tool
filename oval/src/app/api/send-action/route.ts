import { NextResponse } from "next/server";

// Team email routing — in production, this would connect to SendGrid/SES/Slack
const TEAM_CONTACTS: Record<string, { email: string; slack?: string }> = {
  "Product Team": { email: "product@pw.live", slack: "#product-engineering" },
  "Finance Team": { email: "finance@pw.live", slack: "#finance-alerts" },
  "Legal Team": { email: "legal@pw.live", slack: "#legal-alerts" },
  "HR Team": { email: "hr@pw.live", slack: "#hr-alerts" },
  "Batch Operations Team": { email: "batch-ops@pw.live", slack: "#batch-operations" },
  "YouTube Team": { email: "youtube@pw.live", slack: "#youtube-content" },
  "PR Team": { email: "pr@pw.live", slack: "#pr-war-room" },
  "Vidyapeeth Operations Team": { email: "vidyapeeth@pw.live", slack: "#vidyapeeth-ops" },
  "Marketing Team": { email: "marketing@pw.live", slack: "#marketing-campaigns" },
  "Customer Support Team": { email: "support@pw.live", slack: "#customer-support" },
};

export async function POST(request: Request) {
  const body = await request.json();
  const { actionId, department, taskTitle, taskDescription, evidence, suggestedActions, priority, senderEmail } = body;

  const contact = TEAM_CONTACTS[department];
  if (!contact) {
    return NextResponse.json({ error: "Unknown department" }, { status: 400 });
  }

  // Build email content
  const emailBody = `
OVAL Brand Intelligence Alert
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Department: ${department}
Priority: ${priority?.toUpperCase()}
Task: ${taskTitle}

${taskDescription}

Evidence:
${(evidence || []).map((e: any, i: number) => `  ${i + 1}. [${e.platform}] "${e.text?.slice(0, 150)}"`).join("\n")}

Suggested Actions:
${(suggestedActions || []).map((a: string, i: number) => `  ${i + 1}. ${a}`).join("\n")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sent from OVAL Command Center
Powered by RAG (pgvector + GPT-5.4)
  `.trim();

  // In production: send via SendGrid/SES
  // For MVP: log and return success
  console.log(`[OVAL EMAIL] To: ${contact.email} | Subject: [${priority?.toUpperCase()}] ${taskTitle}`);
  console.log(emailBody);

  return NextResponse.json({
    success: true,
    sentTo: {
      email: contact.email,
      slack: contact.slack,
      department,
    },
    actionId,
    timestamp: new Date().toISOString(),
    message: `Action sent to ${department} team at ${contact.email}`,
  });
}
