import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const { question } = await request.json();

  if (!question) {
    return NextResponse.json({ error: "No question provided" }, { status: 400 });
  }

  return NextResponse.json({ presentation_only: true });
}
