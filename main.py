import sqlalchemy
import scipy
from scipy.stats import spearmanr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import func
import matplotlib.pyplot as plt

engine = create_engine('mysql+pymysql://root:pass@localhost/codesmell', echo=True, encoding='utf-8')
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

def minmax(x,min,max):
    return (x - min) / (max - min)

class CodeSmell(Base):
    __tablename__ = 'expResult_awesome_qr'
    id = Column(Integer, primary_key=True)
    smell = Column(String)
    targetClass = Column(String)
    relatedClass = Column(String)
    targetMethod = Column(String)
    relatedMethod = Column(String)
    intensity = Column(Float)
    approach =  Column(String)
    algo = Column(String)
    algoSub = Column(String)
    projectName = Column(String)
    version = Column(String)
    loc = Column(Integer)

class ProjectCodeSmellReport():

    def init(self,sdcMin,sdcMax,sfeMin,sfeMax,sblobMin,sblobMax):
        self.sdcMin = sdcMin
        self.sdcMax = sdcMax
        self.sfeMin = sfeMin
        self.sfeMax = sfeMax
        self.sblobMin = sblobMin
        self.sblobMax = sblobMax
        self.nStructuralFE=0
        self.nTextualFE=0
        self.nStructuralBlob=0
        self.nTextualBlob=0

        self.allTFE=[]
        self.allTFEI=[]

        self.allSFE=[]
        self.allSFEI=[]

        self.allFEI=[]
        self.allDeterminedFEI=[]

        self.allTBlob=[]
        self.allTBlobI=[]

        self.allSBlob=[]
        self.allSBlobI=[]

        self.allBlobI=[]
        self.allDC=[]
        self.allDCI=[]
        self.allDeterminedDCI=[]


        self.nFE=0
        self.nDC=0
        self.nBlob=0

        self.avgFE=0
        self.avgDC=0
        self.avgBlob=0

        self.projectName=""
        self.classDict={}
        self.classes=set()

        self.C4Dict = {}
        self.C4s=[]
        self.avgC4Diff = 0

    def processSmell(self,smell):
        self.classes.add(smell.targetClass)
        clazz = self.classDict.get(smell.targetClass)
        if smell.relatedClass!=None and smell.intensity>0:
            clazzr = self.classDict.get(smell.relatedClass)
            if clazzr is None:
                clazzr = ClassCodeSmellReport(smell.relatedClass)
            clazzr.processSmell(smell,self)
            self.classDict[smell.relatedClass] = clazzr

        if clazz is None:
            clazz = ClassCodeSmellReport(smell.targetClass)

        if smell.intensity>0:
            clazz.processSmell(smell,self)
            if smell.smell == 'fe':
                if smell.algo != 'cdisp':
                    if smell.approach == 'textual':
                        self.nTextualFE += 1
                        self.allTFE.append(smell)
                    else:
                        self.nStructuralFE += 1
                        self.allSFE.append(smell)
                else:
                    self.nDC += 1
                    self.allDC.append(smell)
            else:
                if smell.approach == 'textual':
                    self.nTextualBlob += 1
                    self.allTBlob.append(smell)
                else:
                    self.nStructuralBlob += 1
                    self.allSBlob.append(smell)
        self.classDict[smell.targetClass]=clazz

    def determine(self):
        sumFE = 0
        sumDC = 0
        sumBlob = 0
        for smell in self.allSFE:
            smell.intensity = minmax(smell.intensity,sfeMin,sfeMax)
            self.allSFEI.append(smell.intensity)

            self.allFEI.append(smell.intensity)

        for smell in self.allSBlob:
            smell.intensity = minmax(smell.intensity,sblobMin,sblobMax)
            self.allSBlobI.append(smell.intensity)

            self.allBlobI.append(smell.intensity)

        for smell in self.allTFE:
            self.allTFEI.append(smell.intensity)

            self.allFEI.append(smell.intensity)

        for smell in self.allTBlob:
            self.allTBlobI.append(smell.intensity)

            self.allBlobI.append(smell.intensity)

        for smell in self.allDC:
            smell.intensity = minmax(smell.intensity,sdcMin,sdcMax)
            self.allDCI.append(smell.intensity)

        for i in self.classes:
            cr = self.classDict[i]
            cr.determine()
            for dfei in cr.IFEs:
                self.allDeterminedFEI.append(dfei)
            for ddci in cr.IDCs:
                self.allDeterminedDCI.append(ddci)
            if cr.avgFE>0 :self.nFE+=1
            if cr.avgDC>0 :self.nDC+=1
            if cr.intBlob>0 :self.nBlob+=1
            if (cr.avgDC>0 or cr.avgFE>0) and cr.intBlob>0 :
            # if len(cr.functions)>0:

                couplingVal = cr.avgFE if cr.avgFE > cr.avgDC else cr.avgDC
                self.C4Dict[cr.className]={
                    'cohesion': cr.intBlob,
                    'coupling_rate': cr.nCoup/len(cr.functions),
                    'dc':cr.avgDC,
                    'fe':cr.avgFE,
                    'coupling':couplingVal,
                    'loc':cr.loc,
                    'nEnviedBy':cr.nEnviedBy
                }
                self.C4Dict[cr.className]['diff']=self.C4Dict[cr.className]['cohesion']-self.C4Dict[cr.className]['coupling']
                self.C4s.append(cr.className)
                self.avgC4Diff+=self.C4Dict[cr.className]['diff']
            sumFE+=cr.avgFE
            sumDC+=cr.avgDC
            sumBlob+=cr.intBlob
        self.avgC4Diff/=len(self.C4s)
        self.avgFE=sumFE/self.nFE
        self.avgDC=sumDC/self.nDC
        self.avgBlob=sumBlob/self.nBlob

class FunctionCodeSmellReport():


    def __init__(self,functionName,className):
        self.functionName = functionName
        self.className = className
        self.intDC=0
        self.intFE=0
        self.intStructuralFE=0
        self.intTextualFE=0
        self.coupling=False

    def processSmell(self,smell,parent):
        if self.functionName != smell.targetMethod or self.className != smell.targetClass:
            return
        i = smell.intensity
        if i > 0:
            self.coupling = True
            if smell.algo == 'cdisp':
                self.intDC = minmax(i,parent.sdcMin,parent.sdcMax)
            elif smell.approach == 'textual':
                self.intTextualFE = i
            else:
                self.intStructuralFE =  minmax(i,parent.sfeMin,parent.sfeMax)

    def determine(self):
       self.intFE = self.intTextualFE if self.intTextualFE > self.intStructuralFE else self.intStructuralFE

class ClassCodeSmellReport():

    def __init__(self,className):
        self.className = className
        self.functionDict = {}
        self.functions = set()
        self.intStructuralBlob = 0
        self.intTextualBlob = 0
        self.intBlob = 0
        self.loc=0


        self.nFE = 0
        self.avgFE = 0

        self.nDC = 0
        self.nCoup = 0
        self.avgDC = 0
        self.IFEs = []
        self.IDCs = []
        self.nBlob = 0

        self.nEnviedBy = 0
        self.enviedBy = set()

        self.coupling = False
        self.cohesion = False

    def processSmell(self,smell,parent):
        func = None

        if self.className == smell.relatedClass:
            self.enviedBy.add(smell.targetClass)
            self.nEnviedBy+=1
            return
        self.loc=smell.loc

        if self.className != smell.targetClass:
            return
        if smell.targetMethod!=None:
            func = self.functionDict.get(smell.targetMethod)
            print(smell.targetMethod + "->" + self.className)
            self.functions.add(smell.targetMethod)
            if func is None:
                func = FunctionCodeSmellReport(smell.targetMethod,self.className)

        if smell.intensity>0:
            if smell.smell == 'fe':
                self.coupling = True
                if func != None:
                    func.processSmell(smell,parent)
            else:
                self.cohesion = True
                self.nBlob += 1
                if smell.approach == 'textual':
                    self.intTextualBlob = smell.intensity
                else:
                    self.intStructuralBlob = minmax(smell.intensity,parent.sblobMin,parent.sblobMax)
        self.functionDict[smell.targetMethod]=func

    def determine(self):
        self.intBlob = self.intTextualBlob if self.intTextualBlob > self.intStructuralBlob else self.intStructuralBlob
        sumFE = 0
        sumDC = 0
        for i in self.functions:
            fr = self.functionDict[i]
            fr.determine()
            if fr.intFE>0 :
                self.IFEs.append(fr.intFE)
                self.nFE+=1
            if fr.intDC>0 :
                self.IDCs.append(fr.intDC)
                self.nDC+=1
            if fr.intFE>0 or fr.intDC>0 : self.nCoup+=1
            sumFE+=fr.intFE
            sumDC+=fr.intDC
        l = len(self.functions)

        self.avgFE=0 if l == 0 else sumFE/l
        self.avgDC=0 if l == 0 else sumDC/l

classReport={}
projectName = "three.js"
# projectName = "awesome_qr"

globalReport = ProjectCodeSmellReport()
globalReport.projectName=projectName
classKeys=[]
sdcMin = 0
sdcMax = 0
sfeMin = 0
sfeMax = 0
sblobMin = 0
sblobMax = 0
for (min,max) in session.query(func.min(CodeSmell.intensity), func.max(CodeSmell.intensity)).filter_by(projectName=projectName, algo='cdisp'):
    sdcMin = min
    sdcMax = max

for (min,max) in session.query(func.min(CodeSmell.intensity), func.max(CodeSmell.intensity)).filter_by(projectName=projectName, algo='JDeodorant'):
    sfeMin = min
    sfeMax = max

for (min,max) in session.query(func.min(CodeSmell.intensity), func.max(CodeSmell.intensity)).filter_by(projectName=projectName, algo='DECOR'):
    sblobMin = min
    sblobMax = max


globalReport.init(sdcMin,sdcMax,sfeMin,sfeMax,sblobMin,sblobMax)

for smell in session.query(CodeSmell).filter_by(projectName=projectName):
    # classKeys.append(smell.targetClass)
    # r = classReport.get(smell.targetClass,None)
    # if r is None:
    #     r = ClassCodeSmellReport()
    #     r.className=smell.targetClass
    # r.processSmell(smell)
    # classReport[smell.targetClass]=r
    globalReport.processSmell(smell)

globalReport.determine()

coupling = []
dc = []
fe = []
coupling_rate = []
loc=[]
cohesion = []
nEnviedBy = []
ncoupling = 0
ncohesion = 0
for k in globalReport.C4s:
    # if globalReport.C4Dict[k]['coupling_rate'] < 0.5 : continue
    dc.append(globalReport.C4Dict[k]['dc'])
    fe.append(globalReport.C4Dict[k]['fe'])
    loc.append(globalReport.C4Dict[k]['loc'])
    coupling.append(globalReport.C4Dict[k]['coupling'])
    if globalReport.C4Dict[k]['coupling']>0 : ncoupling+=1
    coupling_rate.append(globalReport.C4Dict[k]['coupling_rate'])
    cohesion.append(globalReport.C4Dict[k]['cohesion'])
    if globalReport.C4Dict[k]['cohesion']>0 : ncohesion+=1

    nEnviedBy.append(globalReport.C4Dict[k]['nEnviedBy'])
fe_indie = []
blob_indie = []

fig = plt.figure(1, figsize=(9, 6))
label_list=["DC","Structural FE","Textual FE","Structural Blob","Textual Blob"]
size = [globalReport.nDC,globalReport.nStructuralFE,globalReport.nTextualFE,globalReport.nStructuralBlob,globalReport.nTextualBlob]
patches, l_text, p_text = plt.pie(size, labels=label_list, labeldistance=1.1, autopct="%1.1f%%", shadow=False, startangle=90, pctdistance=0.6)
plt.axis("equal")

data_to_plot = [globalReport.allDCI,globalReport.allTFEI,globalReport.allSFEI,globalReport.allTBlobI,globalReport.allSBlobI]
fig = plt.figure(2, figsize=(9, 6))
ax = fig.add_subplot(111)
## Custom x-axis labels
bp = ax.boxplot(data_to_plot)
plt.xticks([1, 2, 3,4,5], ['DC', 'Textual FE', 'Structural FE','Textual Blob', 'Structural Blob'])

data_to_plot = [globalReport.allDeterminedDCI,globalReport.allDeterminedFEI,cohesion]
fig = plt.figure(3, figsize=(9, 6))
ax = fig.add_subplot(111)
## Custom x-axis labels
bp = ax.boxplot(data_to_plot)
plt.xticks([1, 2, 3], ['DC', 'FE', 'BLOB'])

# data_to_plot = [dc,fe,cohesion]
# fig = plt.figure(3, figsize=(9, 6))
# ax = fig.add_subplot(111)
# ## Custom x-axis labels
# bp = ax.boxplot(data_to_plot)
# plt.xticks([1, 2, 3], ['DC', 'FE', 'BLOB'])



fig = plt.figure(4)
subfig1 = fig.add_subplot(1,1,1)
surf1 = plt.plot(coupling, cohesion,'*')
plt.xlabel('Intensity of Class Strong Coupling Smell (Blob)')
plt.ylabel('Intensity of Class Low Cohesion Smells (FE or DC)')


plt.show()

# print(spearmanr(fe,cohesion))
# print(spearmanr(dc,cohesion))
# print(spearmanr(fe,dc))
#
print(spearmanr(coupling,cohesion))
# print(spearmanr(coupling_rate,cohesion))
# print(spearmanr(coupling,loc))
# print(spearmanr(cohesion,loc))

# (c,p) = spearmanr(coupling,cohesion)


print(globalReport.C4s)
print(len(globalReport.C4s))

print(globalReport.C4Dict)

print(globalReport)
print(classReport)