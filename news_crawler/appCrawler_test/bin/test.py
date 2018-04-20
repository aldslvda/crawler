def track_test(s):
    s.append('1')
    return s
def try_catch_test():
    test = []
    try:
        test.append("main")
        1/0
        #return test
    except:
        test.append("except")
        return track_test(test)
    else:
        test.append("else")
        #return test
    finally:
        test.append("finally")
        #print test
        return test.pop()
    #return test
print try_catch_test()

def try_catch_test1():
    test = 0
    try:
        1/0
        #return test
    except:
        test += -1
        return test
    else:
        test = 1
        #return test
    finally:
        test += 2
        return test
    #return test
print try_catch_test1()