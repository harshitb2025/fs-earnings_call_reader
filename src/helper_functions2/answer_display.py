def streaming_answer(prompt, llm):
    wordsperline=25
    words=0
    for chunk in llm.stream(prompt):
        words+=1
        print(chunk.content, end=" ")
        if(words%wordsperline==0):
            print()