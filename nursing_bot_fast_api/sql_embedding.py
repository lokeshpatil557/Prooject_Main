from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from transformers import AutoTokenizer
from langchain.schema import Document

converter = DocumentConverter()
doc1 = converter.convert(r"D:\nursing_chatbot\Clinical-Nursing-Manual.pdf").document
doc2 = converter.convert(r"D:\nursing_chatbot\Manual_Treatment_Specification_v6.2_confidential.pdf").document

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
chunker = HybridChunker(tokenizer=tokenizer, max_tokens=500)

chunks1 = list(chunker.chunk(doc1))
chunks2 = list(chunker.chunk(doc2))

serialized_chunks = [chunker.serialize(chunk) for chunk in (chunks1 + chunks2)]

docs = [Document(page_content=chunk) for chunk in serialized_chunks]




from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
embedding_model = SentenceTransformerEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

from langchain_community.vectorstores import SQLiteVec

db_file = "user_queries.sqlite"  
table_name = "sql_vect"          

db = SQLiteVec.from_documents(
    docs,
    embedding=embedding_model,
    table=table_name,
    db_file=db_file
)

# query = "Volition Target"
# results = db.similarity_search(query, k=3)
# for r in results:
#     print(r.page_content)



# ## TRYING TO USE SQLITE EMBEDDING
# from langchain_community.embeddings.sentence_transformer import (
#     SentenceTransformerEmbeddings,
# )
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import SQLiteVec
import sqlite3

embedding_function =  HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
connection = SQLiteVec.create_connection(db_file=r"D:\nursing_chatbot\nursing_main\user_queries.sqlite")
print("Print Success ,connection object :",connection)
vector_store = SQLiteVec(
    table="sql_vect" , embedding=embedding_function, connection=connection
)


data = vector_store.similarity_search("what is nursing techniques", k=1)

print("data",data)


# import sqlite3
# from langchain_community.vectorstores import SQLiteVec
# #from langchain.embeddings import HuggingFaceEmbeddings
# from langchain_community.embeddings.sentence_transformer import (
#     SentenceTransformerEmbeddings
# )

# # Load embedding model
# embedding_model = SentenceTransformerEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# # Create thread-safe SQLite connection manually
# connection = sqlite3.connect("user_queries.sqlite")

# # Initialize SQLiteVec using your table and connection
# nursing_vectorstore = SQLiteVec(
#     table="sql_vect",
#     embedding=embedding_model,
#     connection=connection
# )


# data = nursing_vectorstore.similarity_search("what is nursing techniques", k=1)
# print("data",data)
