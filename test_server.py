#!/usr/bin/env python3
import asyncio
import json
import logging
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Final updated handle_response function
async def handle_response(response, operation: str):
    """Handle a response from the server, expecting CallToolResult(content=[TextContent(text='...')]) format."""
    try:
        data_container = None
        # Check if the response is a CallToolResult-like object with a 'content' attribute
        if hasattr(response, 'content'):
            data_container = response.content
        else:
             # Handle direct error dicts or other unexpected formats
             if isinstance(response, dict) and "error" in response:
                 logger.error(f"Client library or tool execution error during {operation}: {response['error']}")
                 return None # Indicate error processed
             else:
                 logger.error(f"Unexpected response format received during {operation}: {type(response)} - {str(response)[:200]}...")
                 return {"error": "Unexpected response format received (no content attribute)"}
        
        # Now, check the extracted container (should be the list)
        # Expected format: List containing a single TextContent object
        if isinstance(data_container, list) and len(data_container) == 1:
            content_item = data_container[0]
            # Check if it's the expected TextContent structure
            if hasattr(content_item, 'type') and content_item.type == 'text' and hasattr(content_item, 'text'):
                json_string = content_item.text
                try:
                    # Attempt to parse the JSON string from TextContent
                    # Remove Gerrit's magic prefix just in case it wasn't stripped by the server
                    if json_string.startswith(")]}'"):
                         json_string = json_string[4:]

                    parsed_data = json.loads(json_string.strip())
                    
                    # Check for application-level errors within the parsed JSON
                    if isinstance(parsed_data, dict) and "error" in parsed_data:
                        logger.error(f"Server error during {operation}: {parsed_data['error']}")
                        return None # Indicate server-side error processed
                    
                    # Success! Return the parsed Python object
                    return parsed_data

                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON received from server during {operation}: {json_string[:200]}...")
                    return {"error": "Invalid JSON format received"} # Indicate client-side parsing failure
                except Exception as e:
                    logger.error(f"Error processing parsed JSON during {operation}: {e}")
                    logger.error(traceback.format_exc())
                    return {"error": f"Failed to process parsed JSON: {e}"}
            else:
                # List item was not the expected TextContent
                logger.error(f"Unexpected item type in response list during {operation}: {type(content_item)} - {str(content_item)[:200]}...")
                return {"error": "Unexpected item type in response list"}
        
        # Handle other unexpected formats for the content attribute
        else:
             logger.error(f"Unexpected format for response.content during {operation}: {type(data_container)} - {str(data_container)[:200]}...")
             return {"error": "Unexpected format for response content"}

    except Exception as e:
        # Catch-all for unexpected errors in handle_response itself
        logger.error(f"Unexpected error in handle_response during {operation}: {e}")
        logger.error(traceback.format_exc())
        return None # Indicate failure

async def main():
    # Initialize server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["src/server_direct.py"],
        cwd="."
    )

    logger.info("Testing Gerrit Review Server...\n")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # Test configuration
                logger.info("Validating configuration for Gerrit Review Server...")
                logger.info(f"Gerrit URL: https://gerrit.delivery.epam.com")
                logger.info(f"Username: siarhei_belavus")
                logger.info(f"API Token: ****")

                # Test change ID - using a valid change ID from your Gerrit server
                # change_id = "planner-backend~50996"  # Change ID from planner-backend project
                change_id = "planner-backend~48319" # Using the new change ID provided

                try:
                    # Get commit info
                    logger.info("\nFetching commit info...")
                    commit_info = await session.call_tool("gerrit_get_commit_info", {"change_id": change_id})
                    commit_data = await handle_response(commit_info, "commit info")
                    if commit_data:
                        logger.info("Commit Info:")
                        logger.info(json.dumps(commit_data, indent=2))

                    # Get change detail
                    logger.info("\nFetching change detail...")
                    change_detail = await session.call_tool("gerrit_get_change_detail", {"change_id": change_id})
                    detail_data = await handle_response(change_detail, "change detail")
                    if detail_data:
                        logger.info("Change Detail:")
                        logger.info(json.dumps(detail_data, indent=2))
                        # No longer need to extract revision_id here

                    # Get commit message
                    logger.info("\nFetching commit message...")
                    commit_message = await session.call_tool("gerrit_get_commit_message", {"change_id": change_id})
                    message_data = await handle_response(commit_message, "commit message")
                    if message_data:
                        logger.info("Commit Message:")
                        logger.info(json.dumps(message_data, indent=2))

                    # Get related changes
                    logger.info("\nFetching related changes...")
                    related_changes = await session.call_tool("gerrit_get_related_changes", {
                        "change_id": change_id
                        # No revision_id needed
                    })
                    related_data = await handle_response(related_changes, "related changes")
                    if related_data:
                        logger.info("Related Changes:")
                        logger.info(json.dumps(related_data, indent=2))

                    # Get file list
                    logger.info("\nFetching file list...")
                    file_list = await session.call_tool("gerrit_get_file_list", {
                        "change_id": change_id
                        # No revision_id needed
                    })
                    file_data = await handle_response(file_list, "file list")
                    if file_data:
                        logger.info("File List:")
                        logger.info(json.dumps(file_data, indent=2))

                        if "files" in file_data and isinstance(file_data["files"], dict):
                            # Get diffs for the first few files (if any)
                            files_to_process = list(file_data["files"].keys())[:2] # Limit for testing
                            # all_comments_for_review = [] # No longer needed
                            
                            for file_path in files_to_process:
                                try:
                                    logger.info(f"\nFetching diff for {file_path}...")
                                    diff_info = await session.call_tool("gerrit_get_file_diff", {
                                        "change_id": change_id,
                                        "file_path": file_path
                                    })
                                    diff_data = await handle_response(diff_info, f"file diff for {file_path}")
                                    if diff_data and isinstance(diff_data, dict): # Ensure diff_data is a dict
                                        logger.info(f"Diff for {file_path}:")
                                        logger.info(json.dumps(diff_data, indent=2))

                                        # Post draft comment individually if line changes exist
                                        if "line_changes" in diff_data and diff_data["line_changes"]:
                                            first_change = diff_data["line_changes"][0]
                                            if isinstance(first_change, dict) and "line_number" in first_change:
                                                logger.info(f"\nCreating draft comment on {file_path}:{first_change['line_number']}...")
                                                comment_text = "AI Review Draft: This line was changed." 
                                                
                                                # Call the new draft comment tool
                                                draft_result = await session.call_tool(
                                                    "gerrit_create_draft_comment",
                                                    {
                                                        "change_id": change_id,
                                                        "file_path": file_path,
                                                        "line": first_change["line_number"],
                                                        "message": comment_text
                                                    }
                                                )
                                                draft_result_data = await handle_response(draft_result, f"creating draft comment on {file_path}")
                                                if draft_result_data:
                                                    logger.info("Draft comment creation result:")
                                                    logger.info(json.dumps(draft_result_data, indent=2))
                                            else:
                                                 logger.warning(f"Could not find line_number in first change for {file_path}")

                                            # Test the new set_review tool
                                            logger.info("\nSubmitting review with Code-Review label -1...")
                                            review_result = await session.call_tool(
                                                "gerrit_set_review",
                                                {
                                                    "change_id": change_id,
                                                    "code_review_label": -1,
                                                    "message": "AI Review: Code review completed with non-critical issues."
                                                }
                                            )
                                            review_result_data = await handle_response(review_result, "submitting review")
                                            if review_result_data:
                                                logger.info("Review submission result:")
                                                logger.info(json.dumps(review_result_data, indent=2))
                                        else:
                                            logger.info(f"No line changes found or diff_data structure unexpected for {file_path}")

                                except Exception as e:
                                    logger.error(f"Error processing file {file_path}: {e}")
                                    logger.error(traceback.format_exc())
                        
                            # Remove the block for posting collected review comments
                            # # --- Post all collected comments at once --- 
                            # if all_comments_for_review:
                            #    ...
                            # else:
                            #     logger.info("\nNo comments were collected to post.")
                            # # --- End posting review ---

                        else:
                           logger.warning("'files' key not found or not a dictionary in file_data")

                except Exception as e:
                    logger.error(f"Error during test execution: {e}")
                    logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error initializing server: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())