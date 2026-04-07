from fastapi import UploadFile, File, Form, WebSocket, WebSocketDisconnect, Depends
from jose import JWTError
@app.websocket("/ws/nurse/chat")
async def websocket_nurse_chat(websocket: WebSocket):
    await websocket.accept()

    # Step 1: Get token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_text("❌ Token is missing. Please log in.")
        await websocket.close()
        return

    # Step 2: Validate token
    try:
        current_user = get_current_user_from_token(token)
    except JWTError:
        await websocket.send_text("❌ Invalid or expired token.")
        await websocket.close()
        return

    # Step 3: Check role is nurse
    if not nurse_only(current_user):
        await websocket.send_text("❌ Access denied. Only nurses are allowed.")
        await websocket.close()
        return

    username = current_user.get("username")

    await websocket.send_text(f"✅ Connected as nurse: {username}")

    try:
        while True:
            # 1. Receive the query from frontend
            query = await websocket.receive_text()
           

            # Simulate current_user from token (you can extend this with real auth via query params or headers)
            username = "websocket_nurse"  # You can extract this from headers/token if needed

            try:
                logger.info(f"📩 Nurse '{username}' submitted a query: {query}")

                # Input validation
                input_guard = get_input_guard()
                try:
                    input_guard.validate(query)
                except ValueError as ve:
                    logger.warning(f"⚠️ Input validation failed for user '{username}': {ve}")
                    await websocket.send_text(f"❌ Invalid input: {ve}")
                    continue

                if not re.match(r'^[\x00-\x7F\s]+$', query):
                    logger.warning(f"❌ Non-English query rejected from user '{username}'")
                    await websocket.send_text("❌ Please submit your query in English only.")
                    continue

                # Check if it's a history-related query
                if re.search(r'\b(previous|past|history|asked about|my queries|queries|earlier)\b', query, re.IGNORECASE):
                    logger.info(f"📖 Fetching query history for user '{username}'")
                    response_en = get_user_queries(username, query)
                else:
                    logger.info(f"📚 Retrieving relevant documents for query by user '{username}'")
                    relevant_docs, _ = get_relevant_docs(query, org_id=current_user.get("org_id"))
                    context = format_docs_with_links(relevant_docs)

                    system_prompt = (
                        "You are a highly knowledgeable medical assistant specializing in oncology nursing. "
                        "Always provide evidence-based, clear, and empathetic responses tailored for nurses. "
                        "Use the following context when helpful, but you can also answer using your medical knowledge. "
                        "Always provide useful, medically sound answers. "
                    )

                    prompt = (
                        f"You are a highly knowledgeable medical assistant with expertise in clinical decision making.\n"
                        f"Based on the following medical content:\n{context}\n\n"
                        f"If the information is irrelevant or unknown, respond with:\n"
                        f"First, extract and list only the relevant source links (URLs, PDF files) that are directly related to the user's question.\n"
                        f"Format all links as clickable Markdown hyperlinks, e.g., (URL).\n"
                        f"Only include links if they provide direct value or reference to the question.\n\n"
                        f"Then, provide a detailed and well-structured response that includes:\n"
                        f"- Scientific insights or background information,\n"
                        f"- Practical step-by-step instructions or procedures,\n"
                        f"- Helpful tips or recommendations,\n"
                        f"- And clear, concise explanations that address the user's query thoroughly.\n\n"
                        f"Make sure the answer is engaging, informative, and easy to understand, rather than just a brief reply.\n\n"
                        f"Question: {query}"
                    )

                    full_prompt = system_prompt + "\n\n" + prompt
                    logger.info(f"🤖 Sending prompt to Gemini model for user '{username}'")
                    response_en = query_gemini(full_prompt)

                # Store the query + response
                store_user_query(username, query, response_en)
                logger.info(f"✅ Query successfully processed and stored for user '{username}'")

                # Send the response back over WebSocket
                await websocket.send_text(response_en)

            except Exception as e:
                logger.error(f"❌ Error handling query for user '{username}': {str(e)}")
                await websocket.send_text(f"❌ Internal error: {str(e)}")

    except WebSocketDisconnect:
        print("❌ Nurse disconnected from WebSocket chat")
