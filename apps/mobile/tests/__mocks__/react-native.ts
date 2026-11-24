export const Platform = {
  OS: 'ios',
  select: (objs: any) => objs.ios || objs.default,
};
