#!/usr/bin/env python3

import os
from google import genai
from google.genai import types

def ask_gemini():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash-exp"
    
    prompt = """given this semgrep output

   ❯❯❯❱ javascript.express.db.sequelize-express.sequelize-express

          Untrusted input might be used to build a database query, which can lead to a SQL injection         
          vulnerability. An attacker can execute malicious SQL statements and gain unauthorized access to    
          sensitive data, modify, delete data, or execute arbitrary system commands. To prevent this         
          vulnerability, use prepared statements that do not concatenate user-controllable strings and use   
          parameterized queries where SQL commands and user data are strictly separated. Also, consider using
          an object-relational (ORM) framework to operate with safer abstractions.                           
          Details: https://sg.run/6JKdw                                                                      
                                                                                                             
           23┆ models.sequelize.query(`SELECT * FROM Products WHERE ((name LIKE '%${criteria}%' OR   
               description LIKE '%${criteria}%') AND deletedAt IS NULL) ORDER BY name`) // vuln-code-
               snippet vuln-line unionSqlInjectionChallenge dbSchemaChallenge                        
   
   ❯❯❱ javascript.sequelize.security.audit.sequelize-injection-express.express-sequelize-injection

          Detected a sequelize statement that is tainted by user-input. This could lead to SQL injection if   
          the variable is user-controlled and is not properly sanitized. In order to prevent SQL injection, it
          is recommended to use parameterized queries or prepared statements.                                 
          Details: https://sg.run/gjoe                                                                        
                                                                                                              
           23┆ models.sequelize.query(`SELECT * FROM Products WHERE ((name LIKE '%${criteria}%' OR   
               description LIKE '%${criteria}%') AND deletedAt IS NULL) ORDER BY name`) // vuln-code-
               snippet vuln-line unionSqlInjectionChallenge dbSchemaChallenge   

can you write a rule(s) for the LLM, such that it would prevent these when writing code? 

1) write the rule in general terms so any LLM can use it

2) be succinct where possible"""

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    print(f"🤖 Asking Gemini ({model})...\n")
    print("=" * 80)
    print("RESPONSE:")
    print("=" * 80)
    print()
    
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
    ):
        print(chunk.text, end="", flush=True)
    
    print("\n")
    print("=" * 80)
    print("✅ Response complete!")

if __name__ == "__main__":
    ask_gemini()




