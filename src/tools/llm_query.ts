// src/tools/llm_query.ts

import { shell } from "Developer";

/**
 * Defines the parameters for the LLM.query tool.
 */
interface LLMQueryParams {
  /**
   * The text prompt to send to the language model.
   */
  prompt: string;
  /**
   * The specific model to use (optional). Defaults to Claude's default.
   * Can be 'haiku', 'sonnet', or 'opus'.
   */
  model?: 'haiku' | 'sonnet' | 'opus';
}

/**
 * A tool to send a prompt to the local Claude CLI and return the response directly.
 * This is a zero-cost operation that leverages the existing authentication
 * from the Claude Desktop application, as requested by the Commander.
 * 
 * @param params - An object containing the prompt and optional model name.
 * @returns The text response from the Claude model.
 */
export async function query(params: LLMQueryParams): Promise<string> {
  const { prompt, model } = params;
  
  // Define the absolute path to the claude binary to ensure reliability.
  const claudeBinary = '/home/john/.local/bin/claude';
  
  // Start building the command with the essential '--print' flag for non-interactive output.
  let command = `${claudeBinary} --print`;

  // Append the model argument if one was specified.
  if (model) {
    command += ` --model ${model}`;
  }

  // Properly escape the prompt to handle single quotes and other special characters.
  // This replaces every single quote with an escaped single quote ('\\'').
  const escapedPrompt = prompt.replace(/'/g, "'\\''");
  
  // Append the final, escaped prompt wrapped in single quotes.
  command += ` '${escapedPrompt}'`;

  console.log(`[LLM.query] Executing command: ${command}`);

  try {
    // Execute the shell command.
    const result = await shell({ command: command });

    // If the command produced anything on stderr, it indicates an error.
    if (result.stderr) {
      console.error(`[LLM.query] Error from Claude CLI: ${result.stderr}`);
      // Return a structured error message to the main process for better debugging.
      return `Error executing Claude CLI: ${result.stderr}`;
    }

    // Return the standard output, which contains the model's clean response.
    return result.stdout;
  } catch (error) {
    console.error(`[LLM.query] A critical error occurred while executing the shell command: ${error}`);
    return `Critical error in LLM.query tool: ${error.message}`;
  }
}
