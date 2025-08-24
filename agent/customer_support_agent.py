import os
from typing import Optional, Dict, Any
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from dotenv import load_dotenv
load_dotenv()

try:
    from qdrant_setup import vectorstore
    print("Vectorstore imported successfully")
    VECTORSTORE_AVAILABLE = True
except ImportError as e:
    print(f"Vectorstore import failed: {e}")
    vectorstore = None
    VECTORSTORE_AVAILABLE = False

try:
    from db import get_connection
    print("Database connection imported successfully")
    DB_CONNECTION_AVAILABLE = True
except ImportError as e:
    print(f"Database connection import failed: {e}")
    get_connection = None
    DB_CONNECTION_AVAILABLE = False

class CustomerSupportAgent:
    def __init__(self):
        """Initialize the customer support agent with available components"""
        print("Initializing Customer Support Agent...")
        
        self._setup_environment()
        
        # Initialize LLM
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        print("LLM initialized")
        
        # Initialize components
        self.sql_chain = None
        self.vector_chain = None
        self.vectorstore_retriever = None
        
        # Setup available components
        self._setup_sql_chain()
        self._setup_vector_chain()
        self._setup_router()
        
        # Report status
        self._report_status()
    
    def _setup_environment(self):
        """Setup environment variables safely"""
        print("Checking environment variables...")
        
        # Debug
        db_url = os.getenv("DATABASE_URL")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        print(f"DATABASE_URL: {'Found' if db_url else 'Missing'}")
        print(f"OPENAI_API_KEY: {'Found' if openai_key else 'Missing'}")
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        os.environ["OPENAI_API_KEY"] = openai_key
        
        langchain_key = os.getenv("LANGCHAIN_API_KEY")
        if langchain_key:
            os.environ["LANGCHAIN_API_KEY"] = langchain_key
            print("LangChain API key configured")
        
        # Debug db URL
        if db_url:
            print(f"DATABASE_URL configured: {db_url[:20]}...")
        else:
            print("DATABASE_URL not found in environment")
    
    def _setup_sql_chain(self):
        """Setup PostgreSQL database chain"""
        if not DB_CONNECTION_AVAILABLE:
            print("Database connection not available - SQL queries disabled")
            return
        
        try:
            # Check for database URL
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                print("DATABASE_URL not configured - SQL queries disabled")
                return
            
            # Test connection
            conn = get_connection()
            if not conn:
                print("Database connection failed - SQL queries disabled")
                return
            
            # Initialize SQL components
            db = SQLDatabase.from_uri(db_url)
            self.sql_chain = SQLDatabaseChain.from_llm(
                llm=self.llm,
                db=db,
                verbose=True,
                return_intermediate_steps=True,
            )
            print("SQL database chain initialized")
            
        except Exception as e:
            print(f"SQL setup failed: {e}")
            self.sql_chain = None
    
    def _setup_vector_chain(self):
        """Setup Qdrant vectorstore chain"""
        if not VECTORSTORE_AVAILABLE:
            print("Vectorstore not available - vector search disabled")
            return
        
        try:
            # Setup retriever
            self.vectorstore_retriever = vectorstore.as_retriever(
                search_kwargs={"k": 3}
            )
            
            # Create prompt template
            vector_prompt = PromptTemplate(
                input_variables=["context", "question"],
                template="""Use the following context to answer the customer's question. 
Be helpful, concise, and friendly. If the context doesn't contain relevant information, 
say so politely.

Context: {context}

Question: {question}

Answer:"""
            )
            
            # chain using modern approach 
            from langchain.schema.runnable import RunnablePassthrough
            from langchain.schema.output_parser import StrOutputParser
            
            try:
                # modern approach first
                self.vector_chain = vector_prompt | self.llm | StrOutputParser()
                print("Vector search chain initialized (modern approach)")
            except Exception:
                # fallback to LLMChain if modern approach fails
                from langchain.chains import LLMChain
                self.vector_chain = LLMChain(
                    llm=self.llm,
                    prompt=vector_prompt
                )
                print("Vector search chain initialized (legacy approach)")

            
        except Exception as e:
            print(f"Vector setup failed: {e}")
            self.vector_chain = None
            self.vectorstore_retriever = None
    
    def _setup_router(self):
        """Setup question routing logic"""
        router_prompt = PromptTemplate(
            input_variables=["question", "available_sources"],
            template="""You are a customer support router. Analyze the question and decide the best source.

Available sources: {available_sources}

Question: {question}

Rules:
- Use 'sql' for questions about orders, transactions, account info, specific IDs
- Use 'vector' for product information, recommendations, general knowledge
- Use 'general' for greetings, policies, or when no specific data is needed

Respond with only: sql, vector, or general"""
        )
        
        class RouterParser(BaseOutputParser):
            def parse(self, text: str) -> str:
                text = text.lower().strip()
                if 'sql' in text:
                    return 'sql'
                elif 'vector' in text:
                    return 'vector'
                else:
                    return 'general'
        
        try:
            # Try modern approach first
            from langchain.schema.runnable import RunnablePassthrough
            from langchain.schema.output_parser import StrOutputParser
            
            self.router_chain = router_prompt | self.llm | RouterParser()
            print("Question router initialized (modern approach)")
        except Exception:
            # Fallback to LLMChain
            from langchain.chains import LLMChain
            self.router_chain = LLMChain(
                llm=self.llm,
                prompt=router_prompt,
                output_parser=RouterParser()
            )
            print("Question router initialized (legacy approach)")
    
    def _report_status(self):
        """Report the status of all components"""
        print("\nSystem Status Report:")
        print(f"  SQL Database: {'Available' if self.sql_chain else 'Disabled'}")
        print(f"  Vector Search: {'Available' if self.vector_chain else 'Disabled'}")
        print(f"  General Chat: Available")
        
        if not self.sql_chain and not self.vector_chain:
            print("Warning: Only general chat available. Check your configuration.")
    
    def _get_available_sources(self) -> str:
        """Get list of available data sources"""
        sources = []
        if self.sql_chain:
            sources.append("sql")
        if self.vector_chain:
            sources.append("vector")
        sources.append("general")
        return ", ".join(sources)
    
    def route_question(self, question: str) -> str:
        """Route question to appropriate handler"""
        try:
            available = self._get_available_sources()
            try:
                # Handle both modern and legacy approaches
                if hasattr(self.router_chain, 'invoke'):
                    # Modern approach
                    route = self.router_chain.invoke({
                        "question": question,
                        "available_sources": available
                    })
                else:
                    # Legacy approach
                    route = self.router_chain.run(
                        question=question,
                        available_sources=available
                    )
            except Exception as e:
                print(f"Routing error (inner): {e}")
                return 'general'

            # Validate route is actually available
            if route == 'sql' and not self.sql_chain:
                route = 'vector' if self.vector_chain else 'general'
            elif route == 'vector' and not self.vector_chain:
                route = 'sql' if self.sql_chain else 'general'

            return route

        except Exception as e:
            print(f"Routing error: {e}")
            return 'general'

    
    def handle_sql_query(self, question: str) -> str:
        if not self.sql_chain:
            return "I'm sorry, I cannot access the database right now. Please try again later or contact support."
        
        try:
            print("Querying database...")
            result = self.sql_chain.invoke({"query": question})
            return result["result"]     
        except Exception as e:
            return f"I encountered an issue accessing the database: {str(e)}"

    
    def handle_vector_query(self, question: str) -> str:
        """Handle vector search queries with product-style recommendations"""
        if not self.vector_chain or not self.vectorstore_retriever:
            return "I'm sorry, I cannot search the knowledge base right now. Please try again later."
        
        try:
            print("🔍 Searching knowledge base...")

            # --- Category detection ---
            category_map = {
                "phone": "smartphones",
                "phones": "smartphones",
                "smartphone": "smartphones",
                "tv": "tv",
                "tvs": "tv",
                "television": "tv",
                "laptop": "laptops",
                "laptops": "laptops",
                "watch": "watches",
                "watches": "watches",
                "printer": "printers",
                "printers": "printers",
                "monitor": "monitors",
                "monitors": "monitors",
            }
            
            category_filter = None
            for keyword, cat in category_map.items():
                if keyword in question.lower():
                    category_filter = Filter(
                        must=[FieldCondition(
                            key="metadata.category",
                            match=MatchValue(value=cat)
                        )]
                    )
                    print(f"Applying category filter: {cat}")
                    break

            # --- Run retrieval ---
            if category_filter:
                docs = self.vectorstore_retriever.vectorstore.similarity_search(
                    question, k=5, filter=category_filter
                )
            else:
                docs = self.vectorstore_retriever.invoke(question)

            if not docs:
                return f"I couldn't find any products{f' in category {cat}' if category_filter else ''}."

            # Build richer snippets that include metadata
            product_snippets = "\n".join([
                f"- {doc.page_content} "
                f"(Category: {doc.metadata.get('category', 'N/A')}, "
                f"Price: {doc.metadata.get('price', 'N/A')}, "
                f"Stock: {doc.metadata.get('stock_quantity', 'N/A')})"
                for doc in docs[:5]
            ])
            
            prompt = f"""
    You are a product recommendation assistant.

    The user asked: "{question}"

    Here are candidate products:
    {product_snippets}

    IMPORTANT:
    - Return only products that actually match the category if specified.
    - Include product name and price in your answer.
    - If none match, clearly say so.
    """

            # Use chain to generate recommendation
            if hasattr(self.vector_chain, 'invoke'):
                result = self.vector_chain.invoke({"context": prompt, "question": question})
            else:
                result = self.vector_chain.run(context=prompt, question=question)
            
            return result
        
        except Exception as e:
            return f"I encountered an issue searching our knowledge base: {str(e)}"

    
    def handle_general_query(self, question: str) -> str:
        """Handle general queries with LLM"""
        try:
            print("Processing general inquiry...")
            general_prompt = PromptTemplate(
                input_variables=["question"],
                template="""You are a helpful customer support assistant. 
Answer this question professionally and courteously. If you cannot provide 
specific information, guide the customer on how to get help.

Question: {question}

Answer:"""
            )
            
            
            try:
                # Create general chain
                from langchain.chains import LLMChain
                general_chain = LLMChain(llm=self.llm, prompt=general_prompt)

                # Handle both modern and legacy approaches  
                if hasattr(general_chain, 'invoke'):
                    result = general_chain.invoke({"question": question})
                    return result["text"] if isinstance(result, dict) and "text" in result else str(result)
                else:
                    return general_chain.run(question=question)
            except Exception as chain_error:
                return f"I apologize, but I'm experiencing technical difficulties: {str(chain_error)}"
            
        except Exception as e:
            return "I apologize, but I'm experiencing technical difficulties. Please contact our support team directly."
    
    def ask(self, question: str) -> str:
        """Main method to handle customer questions"""
        print(f"\n❓ Question: {question}")
        
        # Route the question
        route = self.route_question(question)
        print(f"🎯 Route: {route}")
        
        # Handle based on route
        if route == 'sql':
            return self.handle_sql_query(question)
        elif route == 'vector':
            return self.handle_vector_query(question)
        else:
            return self.handle_general_query(question)

# interactive repl
def main():
    """Interactive customer support agent"""
    try:
        # initialize agent
        agent = CustomerSupportAgent()
        
        print("\n" + "="*60)
        print("CUSTOMER SUPPORT AGENT - INTERACTIVE MODE")
        print("="*60)
        print("Type your questions below. Type 'exit' or 'quit' to leave.")
        
        while True:
            try:
                question = input("\n❓ You: ").strip()
                if not question:
                    continue
                if question.lower() in ["exit", "quit"]:
                    print("👋 Goodbye!")
                    break
                
                answer = agent.ask(question)
                print(f"💬 Agent: {answer}")
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure OPENAI_API_KEY is set in your environment")
        print("2. Check that your custom modules (qdrant_setup, db) are accessible")
        print("3. Verify database connections if using SQL features")


if __name__ == "__main__":
    main()