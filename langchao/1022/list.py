class Solution:
    def longestCommonPrefix(self, strs):
        if len(strs) == 0:
            return ''
        if len(strs) == 1:
            return strs[0]
        lens_s = []
        for s in strs:
            lens_s.append(len(s))
        min_s_num = min(lens_s)
        min_index = lens_s.index(min_s_num)

        min_str = strs[min_index]
        num, min_str = self.find_commin(min_s_num, min_str,strs)
        if min_str:
            return min_str
        else:
            return ''

    def find_commin(self, num, min_str, strs):

        for s in strs:
            if min_str[0:num] != s[0:num]:
                num -= 1
                if num > 1:
                    self.find_commin(num, min_str, strs)
                else:
                    return 0, ''
        # print(num)
        # print(min_str)
        # print(min_str[0:num])
        return num, min_str[0:num]

if __name__ == "__main__":
    strs = ["flower","flow","flight"]
    solution = Solution()
    str_return = solution.longestCommonPrefix(strs)
    print(str_return)
        



       

