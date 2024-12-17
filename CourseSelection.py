# Author tangrui
# # 选课系统

# tools
# 1. 过滤课程tool：过滤选修，必修
# 2. 排序课程tool：输入用户的喜好，排序用户喜爱的课程
# 3. 插入用户名称和对应课程tool
# 4. 删除用户名称和对应课程tool
# 5. 用户选课后名称检查，模糊搜索和校正tool

# agent行为
# 1. agent 根据需要选择课程，且将和用户描述比较相似的排在前面
# 2. agent 做好选课和删除课程名称匹配，用户不必说出课程全名或者名称可以是错的，agent会调用chain自动校正
# 3. agent 在检查选课和退选课名称后执行选课或退选操作

from langchain.chat_models import ChatOpenAI
import os
from langchain.agents import tool
from langchain.chains.router import MultiPromptChain
from langchain.chains.router.llm_router import LLMRouterChain,RouterOutputParser
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import langchain
langchain.debug = False
from langchain.agents import load_tools, initialize_agent
from langchain.agents import AgentType
import warnings
warnings.filterwarnings('ignore')

class CourseSelection:
    def __init__(self,user_number,llm_model = "Qwen2.5-14B",key="None",api_base="http://10.58.0.2:8000/v1"):
        CourseSelection.course_dict = {
            "required":[
                "software engineering",
                "machine learning",
                "math",
                "physical",
                "badminton"
            ],
            "elective":[
                "tennis",
                "table tennis",
                "football",
                "deep learning",
                "NLP"
            ]
        }
        self.agent=None
        CourseSelection.user_number = user_number
        CourseSelection.user_select_course = {}
        CourseSelection.user_select_course[CourseSelection.user_number]=[]
        os.environ["OPENAI_API_KEY"] = key
        os.environ["OPENAI_API_BASE"] = api_base
        CourseSelection.llm = ChatOpenAI(temperature=0, model=llm_model)
    

    # 过滤课程tool，llm输入课程类型，过滤对应类型结果
    @staticmethod
    @tool
    def filter_course(course_type:str)->str:
        """
            return course list, use this for filtering courses,
            there two kinds of courses: required , elective
            the input is string type and the content should be required or elective or all
            if user have not asked which kinds of course the input should be all
            the function will return the course list
        """
        if course_type=='all':
            all  = [CourseSelection.course_dict["required"],CourseSelection.course_dict["elective"]]
            return all
        return CourseSelection.course_dict[course_type]

    # 排序用户喜爱的课程
    @staticmethod
    @tool
    def sort_course(user_input:str)->str:
        '''
            do not use this function if user didn't mention his preferences for courses.

            the input is string type and the content should only be the original input
            return sorted course list,if user mentioned the course user liked
            the function will return sorted course list
        '''
        prompt = ChatPromptTemplate.from_template("""
        extract all the course , and sort these course based on the user input
        the courses user liked should be sorted in the front

        the output should only contains the sorted courses with sequence number
                                                
        <<< USER INPUT >>>

        {input}

            <<< COURSE DICT >>>

        """+str(CourseSelection.course_dict["required"]+CourseSelection.course_dict["elective"]))
        llmChain = LLMChain(llm=CourseSelection.llm,prompt=prompt)
        return llmChain.run(user_input)

    # 检查用户提及的课程名称，修正课程
    @staticmethod
    @tool
    def check_course(user_input:str)->str:
        '''
            use this function before user want to quit some courses!
            do not use this function if user didn't decide to select courses or quit/delete courses.
            use this function when user decide to select some courses or quit or delete some courses and you need to check whether the course name user mentioned are correct.
            the input is string type and the content should only be the original input
            return corrected course list
            the function will return corrected course list
        '''
        prompt = ChatPromptTemplate.from_template("""
            extract the course name which user selected from the user input text ,and the course name may not correct
            output the correct course name based on the course list

            the output should only contains the corrected courses name                                             
            <<< USER INPUT >>>
            {input}

            <<< COURSE DICT >>>

        """+str(CourseSelection.course_dict["required"]+CourseSelection.course_dict["elective"]))
        llmChain = LLMChain(llm=CourseSelection.llm,prompt=prompt)
        return llmChain.run(user_input)

    @staticmethod
    @tool
    def select_course(course:str)->str:
        '''
            use this function to record user's selection after checking the course name that user selected.
            the input is string type and the content is the courses that user want to select,
            and the  format should like this: course name 1, course name 2, course name 3 , ...
            the function will return operation info
            the function will return success or the course name that failed to select
        '''
        print("input-on-select:"+course)
        is_succeed = "success"
        all_course =  CourseSelection.course_dict['required']+CourseSelection.course_dict['elective']
        courses_input_lists = course.split(',')
        legal_selected_courses =[c.strip() for c in courses_input_lists if c.strip() in all_course]
        cc = [c.strip() for c in courses_input_lists if c.strip() not in legal_selected_courses]
        if len(cc)>=1:
            print("***:选择时，存在一门课名称非法:"+str(cc))
            is_succeed='failed'
        if CourseSelection.user_number not in CourseSelection.user_select_course:
            CourseSelection.user_select_course[CourseSelection.user_number]=[]
        CourseSelection.user_select_course[CourseSelection.user_number] += [c for c in legal_selected_courses if c not in CourseSelection.user_select_course[CourseSelection.user_number]]
        print(is_succeed)
        return is_succeed
        
    @staticmethod
    @tool
    def quit_course(course:str)->str:
        '''
            before use  this function , you must check where the course name is correct!
            use this function to record user's operation of quiting some courses after checking the course name that user mentioned.
            the input is string type and the content is the courses that user want to quit,
            and the format should like this: course name 1, course name 2, course name 3 , ...
            the function will return operation info
            the function will return success or the course name that failed to quit
        '''
        print("input-on-quit:"+course)
        is_succeed = "success"
        all_course =  CourseSelection.course_dict['required']+CourseSelection.course_dict['elective']
        courses_input_lists = course.split(',')
        legal_selected_courses =[c.strip() for c in courses_input_lists if c.strip() in all_course]
        cc = [c.strip() for c in courses_input_lists if c.strip() not in legal_selected_courses]
        if len(cc)>=1:
            print("***:退选时，存在一门课名称非法:"+str(cc))
            is_succeed='failed'
        if CourseSelection.user_number not in CourseSelection.user_select_course:
            CourseSelection.user_select_course[CourseSelection.user_number]=[]
        CourseSelection.user_select_course[CourseSelection.user_number] = [c for c in CourseSelection.user_select_course[CourseSelection.user_number] if c not in legal_selected_courses]
        print(is_succeed)
        return is_succeed
        
    
    @staticmethod
    @tool
    def view_selected_course(course:str)->str:
        '''
            use this function to show user selected courses.
            the input is string type and the content is always empty,
            the function will return a list of course name that user selected
        '''
        return CourseSelection.user_select_course[CourseSelection.user_number]
        
    def init_agent(self):
        tools = load_tools(["llm-math"], llm=CourseSelection.llm) 
        self.agent= initialize_agent(
            tools+[self.filter_course,self.sort_course,self.check_course,self.select_course
                   ,self.quit_course,self.view_selected_course], 
            CourseSelection.llm, 
            agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True,
            verbose = False)
        
    def serve(self,command):
        return self.agent.run(command)
        
def read_and_print_input():
    user_input = input("请输登记学号开始（输入quit退出）：")
    agent = CourseSelection(user_input)
    agent.init_agent()
    while True:
        user_input = input("Agent服务中（输入quit退出）：")
        if user_input == "quit":
            break
        res = agent.serve(user_input)
        print(res)

if __name__ == "__main__":
    read_and_print_input()